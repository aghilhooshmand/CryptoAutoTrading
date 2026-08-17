"""Session create/start/stop/query and economics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import DecisionJournalRow, RealOrderReconcileRow, SimulationSessionRow, TradeJournalRow
from app.execution.tpsl import derive_levels, validate_percents
from app.market_data.identity import (
    ProductIdentityError,
    identity_api_from_row,
    identity_from_row,
    persistence_columns,
    resolve_product_identity,
)
from app.market_data.models import ALLOWED_INTERVALS, MarketStatus
from app.market_data.service import bound_service_for_identity, get_market_data_service
from app.simulation.accounting import (
    liquidation_equity,
    mark_equity,
    session_net_pnl,
    unrealized_gross,
)
from app.simulation.clock import Clock, SystemClock
from app.execution.port import ExecutionEngine, ExecutionIntent, FillResult
from app.simulation.execution_adapter import execution_engine_for
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d
from app.simulation.pending_confirmation import (
    discard_all_pending_for_session,
    discard_pending,
    expire_due_for_session,
    expire_if_due,
    get_active_pending,
)
from app.simulation.position_sizing import intended_notional
from app.portfolio import repository as portfolio_repo
from app.simulation.control import reasons as risk_reasons
from app.simulation.portfolio_risk import freeze_portfolio_loss_baseline, load_holding_quotes, portfolio_available_amount
from app.simulation.decision_log_mode import (
    effective_decision_log_mode,
    parse_create_decision_log_mode,
)
from app.simulation.final_result import (
    SOURCE_RECOVERY,
    SOURCE_STOP,
    ensure_final_result_backfill,
    final_result_summary,
    parse_final_result,
    persist_final_result,
)
from app.simulation.state_machine import SessionState, recover_to_blocked, transition
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, is_known_strategy_id, validate_and_materialize
from app.strategy.serialize import (
    display_strategy_id,
    dumps_params,
    effective_params_for_row,
)


logger = logging.getLogger(__name__)


class SessionError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        *,
        failed_gates: list[str] | None = None,
        session: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.failed_gates = failed_gates
        self.session = session


def _now(clock: Clock) -> datetime:
    return clock.now()


_ACTIVE_STATES = (
    SessionState.RUNNING.value,
    SessionState.STOPPING.value,
    SessionState.RECOVERY_BLOCKED.value,
)

def _validate_capital(starting: Decimal, allocated: Decimal, max_pos: Decimal) -> None:
    if not (Decimal("0") < max_pos <= allocated <= starting):
        raise SessionError(
            "invalid_config",
            "Require 0 < max_position_size <= allocated_capital <= starting_capital",
        )


def create_session(db: Session, body: dict, clock: Clock | None = None) -> SimulationSessionRow:
    clock = clock or SystemClock()
    mode = body.get("mode", "simulation")
    if mode not in ("simulation", "real"):
        raise SessionError("invalid_config", "mode must be simulation or real", 400)

    try:
        if mode == "real":
            # Local budget only (FR-004b): startingCapital defaults to allocated.
            allocated = d(body.get("allocatedCapital", body.get("startingCapital")))
            starting = allocated
            if body.get("startingCapital") not in (None, ""):
                starting = d(body["startingCapital"])
                if starting != allocated:
                    # Force equality for Real — budget fields must match allocated.
                    starting = allocated
        else:
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

    if mode == "real":
        from app.simulation.real_gates import (
            REAL_ALLOCATED_CAP,
            require_real_credentials,
            try_xt_free_usdt,
        )
        from app.xt_account.errors import CREDENTIALS_MISSING, XtPrivateError

        if allocated > REAL_ALLOCATED_CAP:
            raise SessionError(
                risk_reasons.REAL_CAPITAL_CAP_EXCEEDED,
                risk_reasons.message_for(risk_reasons.REAL_CAPITAL_CAP_EXCEEDED),
                400,
            )
        if not (max_pos > 0 and max_pos <= allocated):
            raise SessionError(
                "invalid_config",
                "Require 0 < max_position_size <= allocated_capital",
            )
        if body.get("symbols") not in (None, "", []):
            raise SessionError("invalid_config", "Real sessions allow exactly one symbol")
        if body.get("positionSide") not in (None, "", "flat"):
            raise SessionError("invalid_config", "Real sessions start flat with at most one long")
        try:
            require_real_credentials()
        except XtPrivateError as exc:
            if exc.code == CREDENTIALS_MISSING:
                raise SessionError(
                    risk_reasons.CREDENTIALS_MISSING,
                    risk_reasons.message_for(risk_reasons.CREDENTIALS_MISSING),
                    503,
                ) from exc
            raise SessionError(exc.code, str(exc), 502) from exc
        free = try_xt_free_usdt()
        if free is not None and free < allocated:
            raise SessionError(
                risk_reasons.INSUFFICIENT_XT_FREE,
                risk_reasons.message_for(risk_reasons.INSUFFICIENT_XT_FREE),
                400,
            )
        allocation_id = None
        portfolio_max_loss_rate = None
        portfolio_max_loss_amount = None
        per_symbol_max_weight = None
    else:
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
                raise SessionError(
                    "invalid_config", f"Invalid portfolioMaxLossAmount: {exc}"
                ) from exc

        per_symbol_max_weight = None
        if body.get("perSymbolMaxWeight") not in (None, ""):
            try:
                w = d(body["perSymbolMaxWeight"])
                if not (Decimal("0") < w <= Decimal("1")):
                    raise SessionError("invalid_config", "perSymbolMaxWeight must be > 0 and ≤ 1")
                per_symbol_max_weight = as_str(w)
            except (ValueError, TypeError) as exc:
                raise SessionError("invalid_config", f"Invalid perSymbolMaxWeight: {exc}") from exc

    try:
        ident = resolve_product_identity(body)
    except ProductIdentityError as exc:
        raise SessionError("invalid_config", str(exc)) from exc
    symbol = ident.symbol_alias
    timeframe = str(body["timeframe"])
    if timeframe not in ALLOWED_INTERVALS:
        raise SessionError(
            "invalid_config",
            "timeframe must be one of: 1m, 5m, 15m, 1h, 4h, 1d",
        )
    if mode == "real" and any(sep in symbol for sep in (",", ";", " ")):
        raise SessionError("invalid_config", "Real sessions allow exactly one symbol")

    try:
        canonical_id, effective_params, _instance = validate_and_materialize(
            body.get("strategyId"),
            body.get("strategyParams"),
        )
    except UnknownStrategyError as exc:
        raise SessionError(exc.code, exc.message, 400) from exc
    except StrategyParamError as exc:
        raise SessionError(exc.code, exc.message, 400) from exc

    try:
        decision_log_mode = parse_create_decision_log_mode(body.get("decisionLogMode"))
    except ValueError as exc:
        raise SessionError("invalid_config", str(exc), 400) from exc

    try:
        tp_pct, sl_pct = validate_percents(
            body.get("takeProfitPercent"),
            body.get("stopLossPercent"),
        )
    except ValueError as exc:
        raise SessionError("invalid_config", str(exc), 400) from exc

    now = _now(clock)
    target_amt = allocated * target_rate
    loss_amt = allocated * loss_rate
    # Real: cash is local budget ceiling only (FR-004b), equal to allocated.
    initial_cash = allocated if mode == "real" else starting
    row = SimulationSessionRow(
        id=str(uuid.uuid4()),
        mode=mode,
        state=SessionState.CONFIGURED.value,
        **persistence_columns(ident),
        timeframe=timeframe,
        starting_capital=as_str(starting if mode == "simulation" else allocated),
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
        cash=as_str(initial_cash),
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
        decision_log_mode=decision_log_mode,
        take_profit_percent=as_str(tp_pct) if tp_pct is not None else None,
        stop_loss_percent=as_str(sl_pct) if sl_pct is not None else None,
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
        .filter(SimulationSessionRow.state.in_(list(_ACTIVE_STATES)))
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

    # Feature 010: Portfolio available at start — Simulation only (Real skips Portfolio).
    if row.mode != "real":
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
        ident = identity_from_row(row)
        service, key = bound_service_for_identity(ident, injected=get_market_data_service())
        await service.get_quote(key)
    except Exception as exc:  # noqa: BLE001
        raise SessionError("market_data_unavailable", "Unable to verify market data for symbol", 503) from exc

    transition(SessionState(row.state), SessionState.RUNNING)
    now = _now(clock)
    row.state = SessionState.RUNNING.value
    row.started_at = now
    row.updated_at = now
    if row.mode != "real":
        quotes = await load_holding_quotes(db)
        freeze_portfolio_loss_baseline(db, row, quotes=quotes)
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
        row.entry_fill_candle_open_time = candle_open_time
        tp_pct = d(row.take_profit_percent) if row.take_profit_percent else None
        sl_pct = d(row.stop_loss_percent) if row.stop_loss_percent else None
        tp_price, sl_price = derive_levels(fill.fill_price, tp_pct, sl_pct)
        row.take_profit_price = as_str(tp_price) if tp_price is not None else None
        row.stop_loss_price = as_str(sl_price) if sl_price is not None else None
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
        row.take_profit_price = None
        row.stop_loss_price = None
        row.entry_fill_candle_open_time = None
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
    if row.mode != "real":
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


async def _safe_mark(row: SimulationSessionRow) -> tuple[Decimal | None, bool]:
    try:
        ident = identity_from_row(row)
        service, key = bound_service_for_identity(ident, injected=get_market_data_service())
        quote = await service.get_quote(key)
    except Exception:  # noqa: BLE001
        return None, False
    if quote.status != MarketStatus.FRESH:
        return None, False
    return d(quote.lastPrice), True


async def force_close_if_needed(
    db: Session,
    row: SimulationSessionRow,
    clock: Clock | None = None,
    engine: ExecutionEngine | None = None,
) -> None:
    clock = clock or SystemClock()
    engine = engine or execution_engine_for(row)
    if row.position_side != "long":
        row.position_flatten_status = "flat" if row.position_side == "flat" else row.position_flatten_status
        return
    mark, safe = await _safe_mark(row)
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
    record_real_order_outcome(db, row, result, side="SELL", clock=clock)
    if result.fill is not None and result.qty is not None:
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
        if row.position_side == "long":
            row.position_flatten_status = "unsafe_unflattened"
        return
    row.position_flatten_status = "unsafe_unflattened"


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
    current = SessionState(row.state)
    if current not in (SessionState.RUNNING, SessionState.RECOVERY_BLOCKED):
        raise SessionError(
            "invalid_state",
            "Session must be RUNNING or RECOVERY_BLOCKED to stop",
            409,
        )
    transition(current, SessionState.STOPPING)
    row.state = SessionState.STOPPING.value
    row.stop_reason = reason
    row.updated_at = _now(clock)
    if row.mode == "real":
        discard_all_pending_for_session(db, row.id, status="cancelled")
    # Clear recovery fields when leaving blocked via stop.
    row.recovery_reason = None
    row.recovery_detail = None
    await force_close_if_needed(db, row, clock=clock)
    transition(SessionState.STOPPING, SessionState.STOPPED)
    row.state = SessionState.STOPPED.value
    row.stopped_at = _now(clock)
    row.updated_at = row.stopped_at
    mark: Decimal | None = None
    safe = False
    m_eq: Decimal | None = None
    if row.position_side == "long":
        mark, safe = await _safe_mark(row)
        if safe and mark is not None:
            m_eq = mark_equity(d(row.cash), d(row.position_qty), mark, row.position_side)
    persist_final_result(
        db,
        row,
        source=SOURCE_STOP,
        frozen_at=row.stopped_at,
        mark_price=mark,
        mark_safe=safe,
        mark_equity=m_eq,
    )
    db.commit()
    db.refresh(row)
    return row


async def resume_session_async(
    db: Session,
    session_id: str,
    clock: Clock | None = None,
) -> SimulationSessionRow:
    """Operator resume from RECOVERY_BLOCKED after full G1–G5 + gap-skip."""
    from app.simulation.gap_skip import apply_offline_gap_skip
    from app.simulation.reconcile import reconcile_session
    from app.simulation.recovery import _mark_safe_for_row

    clock = clock or SystemClock()
    row = get_session(db, session_id)
    if row.state != SessionState.RECOVERY_BLOCKED.value:
        raise SessionError(
            "invalid_state_for_resume",
            "Session must be RECOVERY_BLOCKED to resume",
            409,
        )

    now = _now(clock)
    mark_safe = await _mark_safe_for_row(row)
    if row.mode == "real":
        from app.simulation.pending_confirmation import get_active_pending
        from app.simulation.reconcile import reconcile_real_session
        from app.simulation.recovery import _best_effort_refresh_xt_order

        await _best_effort_refresh_xt_order(row)
        if get_active_pending(db, row.id) is not None:
            row.recovery_reason = risk_reasons.RESUME_UNAVAILABLE
            row.recovery_detail = "Pending Real confirmation still present"
            row.updated_at = now
            db.commit()
            db.refresh(row)
            raise SessionError(
                risk_reasons.RESUME_UNAVAILABLE,
                risk_reasons.message_for(risk_reasons.RESUME_UNAVAILABLE),
                409,
                failed_gates=[risk_reasons.RESUME_UNAVAILABLE],
                session=await session_to_dict(row, db=db),
            )
        result = reconcile_real_session(db, row, mark_safe=mark_safe)
        row.last_recovery_at = now
        if not result.passed:
            reason = result.failed_gates[0] if result.failed_gates else risk_reasons.RESUME_UNAVAILABLE
            row.recovery_reason = reason
            row.recovery_detail = ",".join(result.failed_gates) if result.failed_gates else None
            row.updated_at = now
            db.commit()
            db.refresh(row)
            raise SessionError(
                risk_reasons.RESUME_UNAVAILABLE,
                risk_reasons.message_for(risk_reasons.RESUME_UNAVAILABLE),
                409,
                failed_gates=list(result.failed_gates),
                session=await session_to_dict(row, db=db),
            )
        ok, gap_err = await apply_offline_gap_skip(db, row)
        if not ok:
            row.recovery_reason = gap_err or "recovery_gap_unresolvable"
            row.recovery_detail = gap_err
            row.updated_at = now
            db.commit()
            db.refresh(row)
            raise SessionError(
                risk_reasons.RESUME_UNAVAILABLE,
                "Cannot prove offline gap skip bounds; session remains RECOVERY_BLOCKED.",
                409,
                failed_gates=[gap_err or "recovery_gap_unresolvable"],
                session=await session_to_dict(row, db=db),
            )
        transition(SessionState.RECOVERY_BLOCKED, SessionState.RUNNING)
        row.state = SessionState.RUNNING.value
        row.recovery_reason = None
        row.recovery_detail = None
        row.last_recovery_at = now
        row.updated_at = now
        db.commit()
        db.refresh(row)
        from app.simulation.worker import ensure_worker_running

        ensure_worker_running()
        return row

    result = reconcile_session(db, row, mark_safe=mark_safe)
    row.last_recovery_at = now

    if not result.passed:
        reason = result.failed_gates[0] if result.failed_gates else "reconcile_failed"
        row.recovery_reason = reason
        row.recovery_detail = ",".join(result.failed_gates) if result.failed_gates else None
        row.updated_at = now
        db.commit()
        db.refresh(row)
        raise SessionError(
            "recovery_still_blocked",
            "Reconciliation did not pass; session remains RECOVERY_BLOCKED.",
            409,
            failed_gates=list(result.failed_gates),
            session=await session_to_dict(row, db=db),
        )

    ok, gap_err = await apply_offline_gap_skip(db, row)
    if not ok:
        row.recovery_reason = gap_err or "recovery_gap_unresolvable"
        row.recovery_detail = gap_err
        row.updated_at = now
        db.commit()
        db.refresh(row)
        raise SessionError(
            "recovery_gap_unresolvable",
            "Cannot prove offline gap skip bounds; session remains RECOVERY_BLOCKED.",
            409,
            failed_gates=[gap_err or "recovery_gap_unresolvable"],
            session=await session_to_dict(row, db=db),
        )

    transition(SessionState.RECOVERY_BLOCKED, SessionState.RUNNING)
    row.state = SessionState.RUNNING.value
    row.recovery_reason = None
    row.recovery_detail = None
    row.last_recovery_at = now
    row.updated_at = now
    db.commit()
    db.refresh(row)
    from app.simulation.worker import ensure_worker_running

    ensure_worker_running()
    return row


def _history_list_item(row: SimulationSessionRow) -> dict:
    fr = parse_final_result(row.final_result_json)
    is_real = row.mode == "real"
    return {
        "id": row.id,
        "mode": row.mode,
        "label": "REAL" if is_real else "SIMULATION",
        "state": row.state,
        **identity_api_from_row(row),
        "timeframe": row.timeframe,
        "strategyId": display_strategy_id(row.strategy_id),
        "startedAt": row.started_at.isoformat().replace("+00:00", "Z") if row.started_at else None,
        "stoppedAt": row.stopped_at.isoformat().replace("+00:00", "Z") if row.stopped_at else None,
        "stopReason": row.stop_reason,
        "createdAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
        "finalResultSummary": final_result_summary(fr),
    }


def list_sessions(
    db: Session,
    *,
    state: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    if limit < 1 or limit > 100:
        raise SessionError("invalid_query", "limit must be between 1 and 100", 400)
    if offset < 0:
        raise SessionError("invalid_query", "offset must be >= 0", 400)
    allowed = {
        SessionState.CONFIGURED.value,
        SessionState.RUNNING.value,
        SessionState.STOPPING.value,
        SessionState.RECOVERY_BLOCKED.value,
        SessionState.STOPPED.value,
    }
    if state is not None and state not in allowed:
        raise SessionError(
            "invalid_query",
            "state must be one of: CONFIGURED, RUNNING, STOPPING, RECOVERY_BLOCKED, STOPPED",
            400,
        )

    query = db.query(SimulationSessionRow)
    if state is not None:
        query = query.filter(SimulationSessionRow.state == state)
    total = query.count()
    rows = (
        query.order_by(
            SimulationSessionRow.created_at.desc(),
            SimulationSessionRow.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    sessions = []
    for row in rows:
        if row.state == SessionState.STOPPED.value and not row.final_result_json:
            ensure_final_result_backfill(db, row)
        sessions.append(_history_list_item(row))
    return {
        "sessions": sessions,
        "totalCount": total,
        "limit": limit,
        "offset": offset,
    }


def _portfolio_binding_blocks_delete(db: Session, row: SimulationSessionRow) -> bool:
    if not row.allocation_id:
        return False
    alloc = portfolio_repo.get_allocation(db, row.allocation_id)
    if alloc is not None:
        try:
            reserved = d(alloc.reserved_size)
        except Exception:  # noqa: BLE001
            reserved = Decimal("0")
        if reserved > 0:
            return True
    if row.position_side == "long" and row.cost_basis:
        try:
            if d(row.cost_basis) > 0:
                return True
        except Exception:  # noqa: BLE001
            return True
    return False


def delete_session(db: Session, session_id: str) -> None:
    row = get_session(db, session_id)
    if row.state in _ACTIVE_STATES:
        raise SessionError(
            "session_active",
            "Cannot delete a RUNNING, STOPPING, or RECOVERY_BLOCKED session",
            409,
        )
    if _portfolio_binding_blocks_delete(db, row):
        raise SessionError(
            "portfolio_binding_active",
            "Cannot delete while Portfolio reserved or deployed capital is bound to this session",
            409,
        )
    from app.db.models import SkippedGapAuditRow

    db.query(SkippedGapAuditRow).filter(SkippedGapAuditRow.session_id == session_id).delete(
        synchronize_session=False
    )
    db.query(DecisionJournalRow).filter(DecisionJournalRow.session_id == session_id).delete(
        synchronize_session=False
    )
    db.query(TradeJournalRow).filter(TradeJournalRow.session_id == session_id).delete(
        synchronize_session=False
    )
    db.delete(row)
    db.commit()


def _stopped_economics_from_freeze(row: SimulationSessionRow, freeze: dict) -> dict:
    """Authoritative ending economics from freeze — no live mark drift."""
    return {
        "startEquity": row.starting_capital,
        "cash": freeze.get("cash", row.cash),
        "markEquity": None,
        "markNetPnl": None,
        "unrealizedGross": None,
        "liquidationEquity": freeze.get("endingEquity"),
        "grossPnl": row.cumulative_gross_realized,
        "fees": freeze.get("fees", row.cumulative_fees),
        "slippageCost": freeze.get("slippageCost", row.cumulative_slippage_cost),
        "netPnl": freeze.get("netPnl"),
        "targetNetProfitRate": row.target_net_profit_rate,
        "targetNetProfitAmount": row.target_net_profit_amount,
        "maxSessionLossRate": row.max_session_loss_rate,
        "maxSessionLossAmount": row.max_session_loss_amount,
        "markPrice": None,
        "markSafe": False,
    }


async def economics_dict(row: SimulationSessionRow) -> dict:
    mark, safe = await _safe_mark(row)

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


def _record_real_order_row(
    db: Session,
    row: SimulationSessionRow,
    *,
    client_intent_id: str,
    side: str,
    xt_order_id: str | None,
    submit_status: str,
    reconcile_status: str,
    filled_qty: Decimal | None,
    avg_price: Decimal | None,
    clock: Clock,
) -> None:
    db.add(
        RealOrderReconcileRow(
            id=str(uuid.uuid4()),
            session_id=row.id,
            client_intent_id=client_intent_id,
            xt_order_id=xt_order_id,
            venue_order_id=xt_order_id,
            side=side,
            order_type="MARKET",
            submit_status=submit_status,
            reconcile_status=reconcile_status,
            filled_qty=as_str(filled_qty) if filled_qty is not None else None,
            avg_price=as_str(avg_price) if avg_price is not None else None,
            fee=None,
            updated_at=_now(clock),
        )
    )


def record_real_order_outcome(
    db: Session,
    row: SimulationSessionRow,
    result: FillResult,
    *,
    side: str,
    clock: Clock,
    client_intent_id: str | None = None,
) -> None:
    """Persist XT submit/reconcile metadata for a Real execution attempt."""
    if row.mode != "real":
        return
    row.xt_order_id = result.xt_order_id or row.xt_order_id
    row.venue_order_id = result.venue_order_id or result.xt_order_id or row.venue_order_id
    row.real_submit_status = "submitted" if result.xt_order_id else "submit_failed"
    row.real_reconcile_status = result.reconcile_status
    _record_real_order_row(
        db,
        row,
        client_intent_id=client_intent_id or str(uuid.uuid4()),
        side=side,
        xt_order_id=result.xt_order_id,
        submit_status=row.real_submit_status or "not_submitted",
        reconcile_status=result.reconcile_status or "unsettled",
        filled_qty=result.qty,
        avg_price=result.fill.fill_price if result.fill else None,
        clock=clock,
    )


def block_real_session_if_needed(row: SimulationSessionRow, result: FillResult) -> bool:
    """RUNNING Real session → RECOVERY_BLOCKED when adapter signals blocked."""
    if row.mode != "real" or not result.blocked:
        return False
    if SessionState(row.state) not in (SessionState.RUNNING, SessionState.STOPPING):
        return False
    recover_to_blocked(SessionState(row.state))
    row.state = SessionState.RECOVERY_BLOCKED.value
    row.recovery_reason = result.reason_code
    row.recovery_detail = result.reason_message
    return True


def _apply_real_execution_result(
    db: Session,
    row: SimulationSessionRow,
    pending,
    result,
    *,
    mark: Decimal,
    clock: Clock,
    candle_open_time: int | None = None,
) -> None:
    """Apply RealExecutionAdapter outcome; block session on partial/unsettled."""
    record_real_order_outcome(
        db, row, result, side="BUY", clock=clock, client_intent_id=pending.id
    )

    if result.ok and result.fill is not None and result.qty is not None:
        _apply_fill(
            row,
            side="BUY",
            qty=result.qty,
            fill=result.fill,
            is_forced=False,
            candle_open_time=candle_open_time,
            clock=clock,
            db=db,
        )
        discard_pending(db, pending, status="confirmed")
        add_decision(
            db,
            row,
            signal="BUY",
            outcome="approved",
            candle_open_time=candle_open_time,
            reason_code=None,
            reason_message="Confirmed Real entry (XT reconcile)",
            fast_ema=None,
            slow_ema=None,
            clock=clock,
        )
        return

    if result.fill is not None and result.qty is not None:
        _apply_fill(
            row,
            side="BUY",
            qty=result.qty,
            fill=result.fill,
            is_forced=False,
            candle_open_time=candle_open_time,
            clock=clock,
            db=db,
        )

    discard_pending(db, pending, status="rejected" if not result.blocked else "confirmed")
    if result.blocked:
        recover_to_blocked(SessionState(row.state))
        row.state = SessionState.RECOVERY_BLOCKED.value
        row.recovery_reason = result.reason_code
        row.recovery_detail = result.reason_message
    add_decision(
        db,
        row,
        signal="BUY",
        outcome="rejected",
        candle_open_time=candle_open_time,
        reason_code=result.reason_code,
        reason_message=result.reason_message,
        fast_ema=None,
        slow_ema=None,
        clock=clock,
    )


async def confirm_entry_async(
    db: Session,
    session_id: str,
    clock: Clock | None = None,
) -> SimulationSessionRow:
    clock = clock or SystemClock()
    row = get_session(db, session_id)
    if row.mode != "real":
        raise SessionError("invalid_config", "confirm-entry is only for Real sessions", 400)
    if row.state != SessionState.RUNNING.value:
        raise SessionError("invalid_state", "Session must be RUNNING to confirm entry", 409)

    pending = get_active_pending(db, row.id)
    if pending is None:
        raise SessionError(
            risk_reasons.NO_PENDING_CONFIRMATION,
            risk_reasons.message_for(risk_reasons.NO_PENDING_CONFIRMATION),
            409,
        )

    expire_if_due(db, pending, now=clock.now())
    if pending.status != "pending":
        raise SessionError(
            risk_reasons.PENDING_CONFIRMATION_EXPIRED,
            risk_reasons.message_for(risk_reasons.PENDING_CONFIRMATION_EXPIRED),
            409,
        )

    if row.position_side != "flat":
        discard_pending(db, pending, status="rejected")
        db.commit()
        raise SessionError(
            risk_reasons.CONFIRM_VALIDATION_FAILED,
            "Cannot confirm entry while not flat",
            400,
        )

    from app.simulation.real_gates import REAL_ALLOCATED_CAP, try_xt_free_usdt

    if d(row.allocated_capital) > REAL_ALLOCATED_CAP:
        discard_pending(db, pending, status="rejected")
        db.commit()
        raise SessionError(
            risk_reasons.REAL_CAPITAL_CAP_EXCEEDED,
            risk_reasons.message_for(risk_reasons.REAL_CAPITAL_CAP_EXCEEDED),
            400,
        )

    mark, safe = await _safe_mark(row)
    if not safe or mark is None:
        discard_pending(db, pending, status="rejected")
        db.commit()
        raise SessionError(
            risk_reasons.CONFIRM_VALIDATION_FAILED,
            risk_reasons.message_for(risk_reasons.INVALID_OR_STALE_MARKET_DATA),
            400,
        )

    notional = d(pending.proposed_notional)
    if notional > REAL_ALLOCATED_CAP:
        discard_pending(db, pending, status="rejected")
        db.commit()
        raise SessionError(
            risk_reasons.REAL_CAPITAL_CAP_EXCEEDED,
            risk_reasons.message_for(risk_reasons.REAL_CAPITAL_CAP_EXCEEDED),
            400,
        )

    free = try_xt_free_usdt()
    if free is not None and free < notional:
        discard_pending(db, pending, status="rejected")
        db.commit()
        raise SessionError(
            risk_reasons.INSUFFICIENT_XT_FREE,
            risk_reasons.message_for(risk_reasons.INSUFFICIENT_XT_FREE),
            400,
        )

    engine = execution_engine_for(row)
    intent = ExecutionIntent(
        side="BUY",
        symbol=row.symbol,
        reference_price=mark,
        fee_rate=d(row.fee_rate),
        slippage_rate=d(row.slippage_rate),
        cash=d(row.cash),
        allocated_capital=d(row.allocated_capital),
        max_position_size=d(row.max_position_size),
        position_side=row.position_side,
        position_qty=d(row.position_qty),
    )
    result = engine.execute(intent)
    _apply_real_execution_result(db, row, pending, result, mark=mark, clock=clock)
    row.updated_at = _now(clock)
    db.commit()
    db.refresh(row)
    return row


def decline_entry(db: Session, session_id: str, clock: Clock | None = None) -> SimulationSessionRow:
    clock = clock or SystemClock()
    row = get_session(db, session_id)
    if row.mode != "real":
        raise SessionError("invalid_config", "decline-entry is only for Real sessions", 400)

    pending = get_active_pending(db, row.id)
    if pending is None:
        raise SessionError(
            risk_reasons.NO_PENDING_CONFIRMATION,
            risk_reasons.message_for(risk_reasons.NO_PENDING_CONFIRMATION),
            409,
        )

    expire_if_due(db, pending, now=clock.now())
    if pending.status != "pending":
        raise SessionError(
            risk_reasons.PENDING_CONFIRMATION_EXPIRED,
            risk_reasons.message_for(risk_reasons.PENDING_CONFIRMATION_EXPIRED),
            409,
        )

    discard_pending(db, pending, status="declined")
    add_decision(
        db,
        row,
        signal="BUY",
        outcome="rejected",
        candle_open_time=None,
        reason_code="pending_declined",
        reason_message="Operator declined Real entry confirmation",
        fast_ema=None,
        slow_ema=None,
        clock=clock,
    )
    row.updated_at = _now(clock)
    db.commit()
    db.refresh(row)
    return row


async def session_to_dict(row: SimulationSessionRow, *, db: Session | None = None) -> dict:
    final_result = None
    if row.state == SessionState.STOPPED.value:
        if db is not None:
            final_result = ensure_final_result_backfill(db, row)
        else:
            final_result = parse_final_result(row.final_result_json)
            if final_result is None:
                # Caller without db: build in-memory ledger backfill without commit
                from app.simulation.final_result import build_final_result, SOURCE_BACKFILL

                final_result = build_final_result(row, source=SOURCE_BACKFILL, frozen_at=row.stopped_at)

    if row.state == SessionState.STOPPED.value and final_result is not None:
        economics = _stopped_economics_from_freeze(row, final_result)
    else:
        economics = await economics_dict(row)

    skipped_gap = None
    if db is not None:
        skipped_gap = _latest_skipped_gap(db, row.id)

    pending_confirmation = None
    if row.mode == "real" and db is not None:
        from app.simulation.pending_confirmation import (
            expire_due_for_session,
            get_active_pending,
            pending_to_dict,
        )

        expire_due_for_session(db, row.id)
        pending_confirmation = pending_to_dict(get_active_pending(db, row.id))
        if pending_confirmation is not None:
            db.commit()

    is_real = row.mode == "real"
    return {
        "id": row.id,
        "mode": row.mode,
        "state": row.state,
        **identity_api_from_row(row),
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
        "decisionLogMode": effective_decision_log_mode(row.decision_log_mode),
        "takeProfitPercent": row.take_profit_percent,
        "stopLossPercent": row.stop_loss_percent,
        "entryFillPrice": row.entry_fill_price,
        "takeProfitPrice": row.take_profit_price,
        "stopLossPrice": row.stop_loss_price,
        "cash": row.cash,
        "cashIsLocalBudgetOnly": is_real,
        "startingCapitalIsLocalBudgetOnly": is_real,
        "positionSide": row.position_side,
        "positionQty": row.position_qty,
        "tradeCount": row.trade_count,
        "strategyFillCount": row.strategy_fill_count,
        "startedAt": row.started_at.isoformat().replace("+00:00", "Z") if row.started_at else None,
        "stoppedAt": row.stopped_at.isoformat().replace("+00:00", "Z") if row.stopped_at else None,
        "stopReason": row.stop_reason,
        "positionFlattenStatus": row.position_flatten_status,
        "lastProcessedCandleOpenTime": row.last_processed_candle_open_time,
        "recoveryReason": row.recovery_reason,
        "recoveryDetail": row.recovery_detail,
        "lastRecoveryAt": (
            row.last_recovery_at.isoformat().replace("+00:00", "Z")
            if row.last_recovery_at
            else None
        ),
        "pendingConfirmation": pending_confirmation,
        "realReconcile": (
            {
                "xtOrderId": row.xt_order_id,
                "submitStatus": row.real_submit_status,
                "reconcileStatus": row.real_reconcile_status,
            }
            if is_real
            else None
        ),
        "skippedGap": skipped_gap,
        "economics": economics,
        "finalResult": final_result,
        "label": "REAL" if is_real else "SIMULATION",
    }


def _ms_to_iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _latest_skipped_gap(db: Session, session_id: str) -> dict | None:
    from app.db.models import SkippedGapAuditRow

    audit = (
        db.query(SkippedGapAuditRow)
        .filter(SkippedGapAuditRow.session_id == session_id)
        .order_by(SkippedGapAuditRow.recorded_at.desc())
        .first()
    )
    if audit is None:
        return None
    return {
        "fromOpenTime": _ms_to_iso(audit.from_open_time),
        "toOpenTime": _ms_to_iso(audit.to_open_time),
        "reason": audit.reason,
        "recordedAt": audit.recorded_at.isoformat().replace("+00:00", "Z")
        if audit.recorded_at
        else None,
    }
