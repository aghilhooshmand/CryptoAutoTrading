"""Session create/start/stop/query and economics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import DecisionJournalRow, SimulationSessionRow, TradeJournalRow
from app.market_data.models import ALLOWED_INTERVALS, MarketStatus
from app.market_data.service import get_market_data_service
from app.simulation.accounting import (
    liquidation_equity,
    mark_equity,
    session_net_pnl,
    unrealized_gross,
)
from app.simulation.clock import Clock, SystemClock
from app.simulation.execution.port import ExecutionIntent, SimulationExecutionEngine
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d
from app.portfolio import repository as portfolio_repo
from app.simulation.control import reasons as risk_reasons
from app.simulation.portfolio_risk import freeze_portfolio_loss_baseline, portfolio_available_amount
from app.simulation.state_machine import SessionState, transition
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, is_known_strategy_id, validate_and_materialize
from app.strategy.serialize import (
    display_strategy_id,
    dumps_params,
    effective_params_for_row,
)


logger = logging.getLogger(__name__)


class SessionError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now(clock: Clock) -> datetime:
    return clock.now()


def _validate_capital(starting: Decimal, allocated: Decimal, max_pos: Decimal) -> None:
    if not (Decimal("0") < max_pos <= allocated <= starting):
        raise SessionError(
            "invalid_config",
            "Require 0 < max_position_size <= allocated_capital <= starting_capital",
        )


def create_session(db: Session, body: dict, clock: Clock | None = None) -> SimulationSessionRow:
    clock = clock or SystemClock()
    mode = body.get("mode", "simulation")
    if mode != "simulation":
        raise SessionError("real_money_unavailable", "Real-money mode is unavailable", 400)

    try:
        starting = d(body["startingCapital"])
        allocated = d(body.get("allocatedCapital", body["startingCapital"]))
        max_pos = d(body["maxPositionSize"])
        target_rate = d(body["targetNetProfitRate"])
        loss_rate = d(body["maxSessionLossRate"])
        max_trades = int(body["maxTrades"])
        duration = int(body["durationSeconds"])
        fee_rate = d(body["feeRate"]) if body.get("feeRate") is not None else DEFAULT_FEE_RATE
        slip_rate = (
            d(body["slippageRate"]) if body.get("slippageRate") is not None else DEFAULT_SLIPPAGE_RATE
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise SessionError("invalid_config", f"Invalid configuration: {exc}") from exc

    if target_rate <= 0 or loss_rate <= 0 or max_trades < 1 or duration < 1:
        raise SessionError("invalid_config", "Rates must be > 0; maxTrades/duration >= 1")
    if fee_rate < 0 or slip_rate < 0:
        raise SessionError("invalid_config", "feeRate and slippageRate must be >= 0")

    _validate_capital(starting, allocated, max_pos)

    # Feature 010: allocated must fit Portfolio available at create.
    try:
        available = portfolio_available_amount(db)
    except Exception as exc:  # noqa: BLE001
        raise SessionError(
            risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE,
            risk_reasons.message_for(risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE),
            400,
        ) from exc
    if allocated > available:
        raise SessionError(
            risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE,
            risk_reasons.message_for(risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE),
            400,
        )

    allocation_id = body.get("allocationId")
    if allocation_id is not None and allocation_id != "":
        allocation_id = str(allocation_id)
        alloc = portfolio_repo.get_allocation(db, allocation_id)
        if alloc is None:
            raise SessionError("not_found", "Allocation not found", 400)
    else:
        allocation_id = None

    portfolio_max_loss_rate = None
    portfolio_max_loss_amount = None
    if body.get("portfolioMaxLossRate") not in (None, ""):
        try:
            portfolio_max_loss_rate = as_str(d(body["portfolioMaxLossRate"]))
            if d(portfolio_max_loss_rate) <= 0:
                raise SessionError("invalid_config", "portfolioMaxLossRate must be > 0")
        except (ValueError, TypeError) as exc:
            raise SessionError("invalid_config", f"Invalid portfolioMaxLossRate: {exc}") from exc
    if body.get("portfolioMaxLossAmount") not in (None, ""):
        try:
            portfolio_max_loss_amount = as_str(d(body["portfolioMaxLossAmount"]))
            if d(portfolio_max_loss_amount) <= 0:
                raise SessionError("invalid_config", "portfolioMaxLossAmount must be > 0")
        except (ValueError, TypeError) as exc:
            raise SessionError("invalid_config", f"Invalid portfolioMaxLossAmount: {exc}") from exc

    per_symbol_max_weight = None
    if body.get("perSymbolMaxWeight") not in (None, ""):
        try:
            w = d(body["perSymbolMaxWeight"])
            if not (Decimal("0") < w <= Decimal("1")):
                raise SessionError("invalid_config", "perSymbolMaxWeight must be > 0 and ≤ 1")
            per_symbol_max_weight = as_str(w)
        except (ValueError, TypeError) as exc:
            raise SessionError("invalid_config", f"Invalid perSymbolMaxWeight: {exc}") from exc

    symbol = str(body["symbol"])
    timeframe = str(body["timeframe"])
    if timeframe not in ALLOWED_INTERVALS:
        raise SessionError(
            "invalid_config",
            "timeframe must be one of: 1m, 5m, 15m, 1h, 4h, 1d",
        )

    try:
        canonical_id, effective_params, _instance = validate_and_materialize(
            body.get("strategyId"),
            body.get("strategyParams"),
        )
    except UnknownStrategyError as exc:
        raise SessionError(exc.code, exc.message, 400) from exc
    except StrategyParamError as exc:
        raise SessionError(exc.code, exc.message, 400) from exc

    now = _now(clock)
    target_amt = allocated * target_rate
    loss_amt = allocated * loss_rate
    row = SimulationSessionRow(
        id=str(uuid.uuid4()),
        mode="simulation",
        state=SessionState.CONFIGURED.value,
        symbol=symbol,
        timeframe=timeframe,
        starting_capital=as_str(starting),
        allocated_capital=as_str(allocated),
        max_position_size=as_str(max_pos),
        target_net_profit_rate=as_str(target_rate),
        max_session_loss_rate=as_str(loss_rate),
        target_net_profit_amount=as_str(target_amt),
        max_session_loss_amount=as_str(loss_amt),
        max_trades=max_trades,
        duration_seconds=duration,
        fee_rate=as_str(fee_rate),
        slippage_rate=as_str(slip_rate),
        strategy_id=canonical_id,
        strategy_params=dumps_params(effective_params),
        cash=as_str(starting),
        position_side="flat",
        position_qty="0",
        trade_count=0,
        strategy_fill_count=0,
        cumulative_fees="0",
        cumulative_slippage_cost="0",
        cumulative_gross_realized="0",
        position_flatten_status="n/a",
        allocation_id=allocation_id,
        portfolio_max_loss_rate=portfolio_max_loss_rate,
        portfolio_max_loss_amount=portfolio_max_loss_amount,
        per_symbol_max_weight=per_symbol_max_weight,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_session(db: Session, session_id: str) -> SimulationSessionRow:
    row = db.get(SimulationSessionRow, session_id)
    if row is None:
        raise SessionError("session_not_found", "Session not found", 404)
    return row


def get_active_session(db: Session) -> SimulationSessionRow | None:
    return (
        db.query(SimulationSessionRow)
        .filter(SimulationSessionRow.state.in_([SessionState.RUNNING.value, SessionState.STOPPING.value]))
        .order_by(SimulationSessionRow.updated_at.desc())
        .first()
    )


def start_session(db: Session, session_id: str, clock: Clock | None = None) -> SimulationSessionRow:
    """Sync wrapper — prefer start_session_async from async routes."""
    import asyncio

    return asyncio.run(start_session_async(db, session_id, clock))


async def start_session_async(
    db: Session, session_id: str, clock: Clock | None = None
) -> SimulationSessionRow:
    clock = clock or SystemClock()
    row = get_session(db, session_id)
    if row.state != SessionState.CONFIGURED.value:
        raise SessionError("invalid_state", "Session must be CONFIGURED to start", 409)
    if get_active_session(db) is not None:
        raise SessionError("session_already_active", "Another session is already active", 409)
    if not is_known_strategy_id(row.strategy_id):
        raise SessionError(
            "unknown_strategy",
            f"Cannot start session with unknown strategy: {row.strategy_id}",
            400,
        )

    # Feature 010: re-check Portfolio available at start; freeze max-loss baseline.
    try:
        available = portfolio_available_amount(db)
    except Exception as exc:  # noqa: BLE001
        raise SessionError(
            risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE,
            risk_reasons.message_for(risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE),
            400,
        ) from exc
    if d(row.allocated_capital) > available:
        raise SessionError(
            risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE,
            risk_reasons.message_for(risk_reasons.INSUFFICIENT_PORTFOLIO_AVAILABLE),
            400,
        )
    if row.allocation_id:
        alloc = portfolio_repo.get_allocation(db, row.allocation_id)
        if alloc is None:
            raise SessionError("not_found", "Bound allocation no longer exists", 400)

    try:
        await get_market_data_service().get_quote(row.symbol)
    except Exception as exc:  # noqa: BLE001
        raise SessionError("market_data_unavailable", "Unable to verify market data for symbol", 503) from exc

    transition(SessionState(row.state), SessionState.RUNNING)
    now = _now(clock)
    row.state = SessionState.RUNNING.value
    row.started_at = now
    row.updated_at = now
    freeze_portfolio_loss_baseline(db, row)
    db.commit()
    db.refresh(row)
    from app.simulation.worker import ensure_worker_running

    ensure_worker_running()
    return row


def _apply_fill(
    row: SimulationSessionRow,
    *,
    side: str,
    qty: Decimal,
    fill,
    is_forced: bool,
    candle_open_time: int | None,
    clock: Clock,
    db: Session,
) -> TradeJournalRow:
    now = _now(clock)
    cash = d(row.cash) + fill.cash_delta
    row.cash = as_str(cash)
    row.cumulative_fees = as_str(d(row.cumulative_fees) + fill.fee)
    row.cumulative_slippage_cost = as_str(d(row.cumulative_slippage_cost) + fill.slippage_cost)
    row.trade_count += 1
    if not is_forced:
        row.strategy_fill_count += 1

    if side == "BUY":
        row.position_side = "long"
        row.position_qty = as_str(qty)
        row.entry_ref_price = as_str(fill.reference_price)
        row.entry_fill_price = as_str(fill.fill_price)
        row.entry_fee = as_str(fill.fee)
        row.entry_slippage_cost = as_str(fill.slippage_cost)
        row.cost_basis = as_str(fill.notional + fill.fee)
        row.position_flatten_status = "n/a"
    else:
        if row.entry_ref_price:
            gross = (fill.reference_price - d(row.entry_ref_price)) * qty
            row.cumulative_gross_realized = as_str(d(row.cumulative_gross_realized) + gross)
        row.position_side = "flat"
        row.position_qty = "0"
        row.entry_ref_price = None
        row.entry_fill_price = None
        row.entry_fee = None
        row.entry_slippage_cost = None
        row.cost_basis = None
        row.position_flatten_status = "forced_closed" if is_forced else "flat"

    trade = TradeJournalRow(
        id=str(uuid.uuid4()),
        session_id=row.id,
        created_at=now,
        symbol=row.symbol,
        side=side,
        qty=as_str(qty),
        reference_price=as_str(fill.reference_price),
        fill_price=as_str(fill.fill_price),
        fee=as_str(fill.fee),
        slippage_cost=as_str(fill.slippage_cost),
        notional=as_str(fill.notional),
        cash_delta=as_str(fill.cash_delta),
        is_forced_close=is_forced,
        candle_open_time=candle_open_time,
    )
    db.add(trade)
    row.updated_at = now
    try:
        from app.portfolio import service as portfolio_svc

        portfolio_svc.try_apply_simulation_fill(
            db,
            symbol=row.symbol,
            side=side,
            qty=qty,
            cash_delta=fill.cash_delta,
            fill_price=fill.fill_price,
        )
    except Exception:
        logger.exception("Simulation Portfolio fill apply failed; session journals kept")
    return trade


def add_decision(
    db: Session,
    row: SimulationSessionRow,
    *,
    signal: str,
    outcome: str,
    candle_open_time: int | None,
    reason_code: str | None,
    reason_message: str | None,
    fast_ema: str | None,
    slow_ema: str | None,
    clock: Clock,
) -> DecisionJournalRow:
    now = _now(clock)
    entry = DecisionJournalRow(
        id=str(uuid.uuid4()),
        session_id=row.id,
        created_at=now,
        candle_open_time=candle_open_time,
        signal=signal,
        outcome=outcome,
        reason_code=reason_code,
        reason_message=reason_message,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
    )
    db.add(entry)
    row.updated_at = now
    return entry


async def _safe_mark(symbol: str) -> tuple[Decimal | None, bool]:
    try:
        quote = await get_market_data_service().get_quote(symbol)
    except Exception:  # noqa: BLE001
        return None, False
    if quote.status != MarketStatus.FRESH:
        return None, False
    return d(quote.lastPrice), True


async def force_close_if_needed(
    db: Session,
    row: SimulationSessionRow,
    clock: Clock | None = None,
    engine: SimulationExecutionEngine | None = None,
) -> None:
    clock = clock or SystemClock()
    engine = engine or SimulationExecutionEngine()
    if row.position_side != "long":
        row.position_flatten_status = "flat" if row.position_side == "flat" else row.position_flatten_status
        return
    mark, safe = await _safe_mark(row.symbol)
    if not safe or mark is None:
        row.position_flatten_status = "unsafe_unflattened"
        return
    intent = ExecutionIntent(
        side="SELL",
        symbol=row.symbol,
        reference_price=mark,
        fee_rate=d(row.fee_rate),
        slippage_rate=d(row.slippage_rate),
        cash=d(row.cash),
        allocated_capital=d(row.allocated_capital),
        max_position_size=d(row.max_position_size),
        position_side=row.position_side,
        position_qty=d(row.position_qty),
        is_forced_close=True,
    )
    result = engine.execute(intent)
    if not result.ok or result.fill is None or result.qty is None:
        row.position_flatten_status = "unsafe_unflattened"
        return
    _apply_fill(
        row,
        side="SELL",
        qty=result.qty,
        fill=result.fill,
        is_forced=True,
        candle_open_time=None,
        clock=clock,
        db=db,
    )
    add_decision(
        db,
        row,
        signal="SELL",
        outcome="forced",
        candle_open_time=None,
        reason_code="hard_stop_flatten",
        reason_message="Forced full close on session stop",
        fast_ema=None,
        slow_ema=None,
        clock=clock,
    )


def stop_session(
    db: Session,
    session_id: str,
    reason: str,
    clock: Clock | None = None,
) -> SimulationSessionRow:
    import asyncio

    return asyncio.run(stop_session_async(db, session_id, reason, clock))


async def stop_session_async(
    db: Session,
    session_id: str,
    reason: str,
    clock: Clock | None = None,
) -> SimulationSessionRow:
    clock = clock or SystemClock()
    row = get_session(db, session_id)
    if row.state != SessionState.RUNNING.value:
        raise SessionError("invalid_state", "Session must be RUNNING to stop", 409)
    transition(SessionState.RUNNING, SessionState.STOPPING)
    row.state = SessionState.STOPPING.value
    row.stop_reason = reason
    row.updated_at = _now(clock)
    await force_close_if_needed(db, row, clock=clock)
    transition(SessionState.STOPPING, SessionState.STOPPED)
    row.state = SessionState.STOPPED.value
    row.stopped_at = _now(clock)
    row.updated_at = row.stopped_at
    db.commit()
    db.refresh(row)
    return row


async def economics_dict(row: SimulationSessionRow) -> dict:
    mark, safe = await _safe_mark(row.symbol)

    cash = d(row.cash)
    qty = d(row.position_qty)
    start = d(row.starting_capital)
    fee = d(row.fee_rate)
    slip = d(row.slippage_rate)
    if row.position_side == "long" and not safe:
        m_eq = None
        l_eq = None
        urg = None
    else:
        m_eq = mark_equity(cash, qty, mark, row.position_side)
        l_eq = liquidation_equity(cash, qty, mark, row.position_side, fee, slip)
        urg = unrealized_gross(
            qty,
            d(row.entry_ref_price) if row.entry_ref_price else None,
            mark,
            row.position_side,
        )
    net = session_net_pnl(l_eq, start)
    mark_net = session_net_pnl(m_eq, start)
    gross = d(row.cumulative_gross_realized) + (urg or Decimal("0"))
    return {
        "startEquity": row.starting_capital,
        "cash": row.cash,
        "markEquity": as_str(m_eq) if m_eq is not None else None,
        "markNetPnl": as_str(mark_net) if mark_net is not None else None,
        "unrealizedGross": as_str(urg) if urg is not None else None,
        "liquidationEquity": as_str(l_eq) if l_eq is not None else None,
        "grossPnl": as_str(gross),
        "fees": row.cumulative_fees,
        "slippageCost": row.cumulative_slippage_cost,
        "netPnl": as_str(net) if net is not None else None,
        "targetNetProfitRate": row.target_net_profit_rate,
        "targetNetProfitAmount": row.target_net_profit_amount,
        "maxSessionLossRate": row.max_session_loss_rate,
        "maxSessionLossAmount": row.max_session_loss_amount,
        "markPrice": as_str(mark) if mark is not None else None,
        "markSafe": safe,
    }


async def session_to_dict(row: SimulationSessionRow) -> dict:
    return {
        "id": row.id,
        "mode": row.mode,
        "state": row.state,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "strategyId": display_strategy_id(row.strategy_id),
        "strategyParams": effective_params_for_row(row.strategy_id, row.strategy_params),
        "startingCapital": row.starting_capital,
        "allocatedCapital": row.allocated_capital,
        "maxPositionSize": row.max_position_size,
        "targetNetProfitRate": row.target_net_profit_rate,
        "maxSessionLossRate": row.max_session_loss_rate,
        "targetNetProfitAmount": row.target_net_profit_amount,
        "maxSessionLossAmount": row.max_session_loss_amount,
        "maxTrades": row.max_trades,
        "durationSeconds": row.duration_seconds,
        "feeRate": row.fee_rate,
        "slippageRate": row.slippage_rate,
        "allocationId": row.allocation_id,
        "portfolioMaxLossRate": row.portfolio_max_loss_rate,
        "portfolioMaxLossAmount": row.portfolio_max_loss_amount,
        "portfolioLossBaselineKind": row.portfolio_loss_baseline_kind,
        "portfolioLossBaselineValue": row.portfolio_loss_baseline_value,
        "perSymbolMaxWeight": row.per_symbol_max_weight,
        "cash": row.cash,
        "positionSide": row.position_side,
        "positionQty": row.position_qty,
        "tradeCount": row.trade_count,
        "strategyFillCount": row.strategy_fill_count,
        "startedAt": row.started_at.isoformat().replace("+00:00", "Z") if row.started_at else None,
        "stoppedAt": row.stopped_at.isoformat().replace("+00:00", "Z") if row.stopped_at else None,
        "stopReason": row.stop_reason,
        "positionFlattenStatus": row.position_flatten_status,
        "lastProcessedCandleOpenTime": row.last_processed_candle_open_time,
        "economics": await economics_dict(row),
        "label": "SIMULATION",
    }
