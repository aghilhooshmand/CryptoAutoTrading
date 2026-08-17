"""Closed-candle pipeline: market data → strategy → control → risk → execution."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow, TradeJournalRow
from app.execution.tpsl import evaluate_triggers
from app.market_data.identity import identity_from_row
from app.market_data.models import MarketStatus
from app.market_data.public_retry import PublicRetryExhausted, with_public_retry
from app.market_data.service import bound_service_for_identity, get_market_data_service
from app.simulation.accounting import liquidation_equity, session_net_pnl
from app.simulation.clock import Clock
from app.simulation.control.controller import TradingController
from app.simulation.control.risk import UNSAFE_QUOTE_LIMIT, RiskContext, RiskManager
from app.simulation.decision_log_mode import should_persist_hold
from app.simulation.execution.port import ExecutionIntent
from app.simulation.execution_adapter import execution_engine_for
from app.simulation.money import as_str, d
from app.simulation.pending_confirmation import create_pending, expire_due_for_session, get_active_pending
from app.simulation.position_sizing import intended_notional
from app.simulation.session_service import (
    _apply_fill,
    add_decision,
    block_real_session_if_needed,
    record_real_order_outcome,
    stop_session_async,
)
from app.simulation.state_machine import SessionState
from app.strategy.base import CandleClose, SignalSide, StrategySignal, bar_high, bar_low
from app.strategy.registry import UnknownStrategyError, build_from_stored
from app.strategy.serialize import loads_params

INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


def _as_utc(dt: datetime) -> datetime:
    """SQLite often returns naive datetimes; clock is always UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _closed_candles(row: SimulationSessionRow, clock: Clock) -> list[CandleClose]:
    ident = identity_from_row(row)
    service, key = bound_service_for_identity(ident, injected=get_market_data_service())

    async def _call():
        return await service.get_candles(key, row.timeframe)

    series = await with_public_retry(_call)
    interval = INTERVAL_SECONDS[row.timeframe]
    now_ms = int(clock.now().timestamp() * 1000)
    closed: list[CandleClose] = []
    for c in series.candles:
        if c.openTime + interval * 1000 <= now_ms:
            closed.append(
                CandleClose(
                    open_time=c.openTime,
                    close=d(c.close),
                    open=d(c.open),
                    high=d(c.high),
                    low=d(c.low),
                )
            )
    return closed


async def _quote_mark(row: SimulationSessionRow) -> tuple[Decimal | None, bool]:
    ident = identity_from_row(row)
    service, key = bound_service_for_identity(ident, injected=get_market_data_service())
    try:

        async def _call():
            return await service.get_quote(key)

        quote = await with_public_retry(_call)
    except (PublicRetryExhausted, Exception):  # noqa: BLE001
        return None, False
    if quote.status != MarketStatus.FRESH:
        return None, False
    return d(quote.lastPrice), True


def _trade_exists_for_candle(
    db: Session, session_id: str, candle_open_time: int | None
) -> bool:
    if candle_open_time is None:
        return False
    return (
        db.query(TradeJournalRow)
        .filter(
            TradeJournalRow.session_id == session_id,
            TradeJournalRow.candle_open_time == candle_open_time,
            TradeJournalRow.is_forced_close.is_(False),
        )
        .first()
        is not None
    )


async def _try_protective_exit(
    db: Session,
    row: SimulationSessionRow,
    *,
    candle: CandleClose,
    mark: Decimal,
    safe: bool,
    clock: Clock,
) -> bool:
    """Evaluate TP/SL after hard-stops; execute forced SELL on live mark if triggered.

    Returns True when this candle was fully handled (caller should return).
    """
    if row.position_side != "long":
        return False
    tp_price = d(row.take_profit_price) if row.take_profit_price else None
    sl_price = d(row.stop_loss_price) if row.stop_loss_price else None
    if tp_price is None and sl_price is None:
        return False

    reason = evaluate_triggers(
        candle_open_time=candle.open_time,
        high=bar_high(candle),
        low=bar_low(candle),
        entry_fill_candle_open_time=row.entry_fill_candle_open_time,
        tp_price=tp_price,
        sl_price=sl_price,
    )
    if reason is None:
        return False

    signal = StrategySignal(
        side=SignalSide.SELL,
        candle_open_time=candle.open_time,
        fast_ema=None,
        slow_ema=None,
        reason_code=reason,
    )
    controller = TradingController()
    risk = RiskManager()
    engine = execution_engine_for(row)

    ctrl = controller.review(SessionState(row.state), signal)
    if not ctrl.approved:
        add_decision(
            db,
            row,
            signal="SELL",
            outcome="rejected",
            candle_open_time=candle.open_time,
            reason_code=ctrl.reason_code,
            reason_message=ctrl.reason_message,
            fast_ema=None,
            slow_ema=None,
            clock=clock,
        )
        row.last_processed_candle_open_time = candle.open_time
        db.commit()
        return True

    from app.simulation.portfolio_risk import apply_portfolio_context, load_holding_quotes

    rctx_kwargs = dict(
        position_side=row.position_side,
        cash=d(row.cash),
        qty=d(row.position_qty),
        fee_rate=d(row.fee_rate),
        slippage_rate=d(row.slippage_rate),
        start_equity=d(row.starting_capital),
        target_net_profit_amount=d(row.target_net_profit_amount),
        max_session_loss_amount=d(row.max_session_loss_amount),
        strategy_fill_count=row.strategy_fill_count,
        max_trades=row.max_trades,
        mark_price=mark,
        mark_safe=safe,
    )
    quotes = await load_holding_quotes(db)
    apply_portfolio_context(rctx_kwargs, db=db, row=row, quotes=quotes)
    rctx = RiskContext(**rctx_kwargs)
    risk_dec = risk.review(signal, rctx)
    if not risk_dec.approved:
        add_decision(
            db,
            row,
            signal="SELL",
            outcome="rejected",
            candle_open_time=candle.open_time,
            reason_code=risk_dec.reason_code,
            reason_message=risk_dec.reason_message,
            fast_ema=None,
            slow_ema=None,
            clock=clock,
        )
        row.last_processed_candle_open_time = candle.open_time
        db.commit()
        if risk_dec.trigger_stop:
            await stop_session_async(db, row.id, risk_dec.trigger_stop, clock=clock)
        return True

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
            candle_open_time=candle.open_time,
            clock=clock,
            db=db,
        )
        add_decision(
            db,
            row,
            signal="SELL",
            outcome="forced",
            candle_open_time=candle.open_time,
            reason_code=reason,
            reason_message=f"Protective exit ({reason})",
            fast_ema=None,
            slow_ema=None,
            clock=clock,
        )
        if not result.ok:
            add_decision(
                db,
                row,
                signal="SELL",
                outcome="rejected",
                candle_open_time=candle.open_time,
                reason_code=result.reason_code,
                reason_message=result.reason_message,
                fast_ema=None,
                slow_ema=None,
                clock=clock,
            )
        block_real_session_if_needed(row, result)
        row.last_processed_candle_open_time = candle.open_time
        db.commit()
        return True

    add_decision(
        db,
        row,
        signal="SELL",
        outcome="rejected",
        candle_open_time=candle.open_time,
        reason_code=result.reason_code,
        reason_message=result.reason_message,
        fast_ema=None,
        slow_ema=None,
        clock=clock,
    )
    block_real_session_if_needed(row, result)
    row.last_processed_candle_open_time = candle.open_time
    db.commit()
    return True


async def process_session_tick(db: Session, row: SimulationSessionRow, clock: Clock) -> None:
    if row.state != SessionState.RUNNING.value:
        return

    if row.mode == "real":
        expire_due_for_session(db, row.id, now=clock.now())

    if row.started_at is not None:
        elapsed = (clock.now() - _as_utc(row.started_at)).total_seconds()
        if elapsed >= row.duration_seconds:
            await stop_session_async(db, row.id, "duration_elapsed", clock=clock)
            return

    mark, safe = await _quote_mark(row)
    if not safe:
        # Unsafe mark: increment streak; while long, early return blocks entries
        # (Risk would also reject; we never reach strategy on unsafe mark).
        row.unsafe_quote_streak += 1
        row.updated_at = clock.now()
        db.commit()
        if row.unsafe_quote_streak >= UNSAFE_QUOTE_LIMIT:
            await stop_session_async(db, row.id, "unrecoverable_unsafe_market_data", clock=clock)
        return
    row.unsafe_quote_streak = 0

    liq = liquidation_equity(
        d(row.cash),
        d(row.position_qty),
        mark,
        row.position_side,
        d(row.fee_rate),
        d(row.slippage_rate),
    )
    net = session_net_pnl(liq, d(row.starting_capital))
    if net is not None:
        if net >= d(row.target_net_profit_amount):
            await stop_session_async(db, row.id, "profit_target", clock=clock)
            return
        if net <= -d(row.max_session_loss_amount):
            await stop_session_async(db, row.id, "max_loss", clock=clock)
            return

    if row.strategy_fill_count >= row.max_trades:
        await stop_session_async(db, row.id, "max_trades", clock=clock)
        return

    try:
        closes = await _closed_candles(row, clock)
    except (PublicRetryExhausted, Exception):  # noqa: BLE001
        row.unsafe_quote_streak += 1
        row.updated_at = clock.now()
        db.commit()
        if row.unsafe_quote_streak >= UNSAFE_QUOTE_LIMIT:
            await stop_session_async(db, row.id, "unrecoverable_unsafe_market_data", clock=clock)
        return

    if not closes:
        db.commit()
        return

    newest = closes[-1]
    if (
        row.last_processed_candle_open_time is not None
        and newest.open_time <= row.last_processed_candle_open_time
    ):
        db.commit()
        return

    assert mark is not None
    if await _try_protective_exit(
        db, row, candle=newest, mark=mark, safe=safe, clock=clock
    ):
        return

    try:
        params = loads_params(row.strategy_params)
        strategy = build_from_stored(row.strategy_id, params)
    except UnknownStrategyError:
        await stop_session_async(
            db,
            row.id,
            "unknown_strategy",
            clock=clock,
        )
        return

    signal = strategy.evaluate(closes)
    controller = TradingController()
    risk = RiskManager()

    ctrl = controller.review(SessionState(row.state), signal)
    if signal.side == SignalSide.HOLD:
        if should_persist_hold(row.decision_log_mode):
            add_decision(
                db,
                row,
                signal="HOLD",
                outcome="hold",
                candle_open_time=signal.candle_open_time,
                reason_code=signal.reason_code,
                reason_message=None,
                fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
                slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
                clock=clock,
            )
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        return

    if not ctrl.approved:
        add_decision(
            db,
            row,
            signal=signal.side.value,
            outcome="rejected",
            candle_open_time=signal.candle_open_time,
            reason_code=ctrl.reason_code,
            reason_message=ctrl.reason_message,
            fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
            slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
            clock=clock,
        )
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        return

    from app.simulation.portfolio_risk import apply_portfolio_context, load_holding_quotes

    rctx_kwargs = dict(
        position_side=row.position_side,
        cash=d(row.cash),
        qty=d(row.position_qty),
        fee_rate=d(row.fee_rate),
        slippage_rate=d(row.slippage_rate),
        start_equity=d(row.starting_capital),
        target_net_profit_amount=d(row.target_net_profit_amount),
        max_session_loss_amount=d(row.max_session_loss_amount),
        strategy_fill_count=row.strategy_fill_count,
        max_trades=row.max_trades,
        mark_price=mark,
        mark_safe=safe,
    )
    quotes = await load_holding_quotes(db)
    apply_portfolio_context(rctx_kwargs, db=db, row=row, quotes=quotes)
    rctx = RiskContext(**rctx_kwargs)
    risk_dec = risk.review(signal, rctx)
    if not risk_dec.approved:
        add_decision(
            db,
            row,
            signal=signal.side.value,
            outcome="rejected",
            candle_open_time=signal.candle_open_time,
            reason_code=risk_dec.reason_code,
            reason_message=risk_dec.reason_message,
            fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
            slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
            clock=clock,
        )
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        if risk_dec.trigger_stop:
            await stop_session_async(db, row.id, risk_dec.trigger_stop, clock=clock)
        return

    # Real exposure-increasing BUY: confirmation gate (no XT until operator confirm).
    if (
        row.mode == "real"
        and signal.side == SignalSide.BUY
        and row.position_side == "flat"
    ):
        if get_active_pending(db, row.id) is not None:
            row.last_processed_candle_open_time = newest.open_time
            db.commit()
            return
        notional = intended_notional(
            d(row.cash),
            d(row.fee_rate),
            d(row.allocated_capital),
            d(row.max_position_size),
        )
        create_pending(
            db,
            session_id=row.id,
            symbol=row.symbol,
            proposed_notional=notional,
            reference_price=mark,
            now=clock.now(),
        )
        add_decision(
            db,
            row,
            signal="BUY",
            outcome="pending_confirmation",
            candle_open_time=signal.candle_open_time,
            reason_code="awaiting_real_confirm",
            reason_message="Real BUY awaiting operator confirmation",
            fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
            slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
            clock=clock,
        )
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        return

    # Idempotency: refuse duplicate fill for same candle (restart / retry).
    if (
        row.last_processed_candle_open_time is not None
        and signal.candle_open_time is not None
        and signal.candle_open_time <= row.last_processed_candle_open_time
    ) or _trade_exists_for_candle(db, row.id, signal.candle_open_time):
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        return

    engine = execution_engine_for(row)
    intent = ExecutionIntent(
        side=signal.side.value,
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
    record_real_order_outcome(db, row, result, side=signal.side.value, clock=clock)
    if result.fill is not None and result.qty is not None:
        _apply_fill(
            row,
            side=signal.side.value,
            qty=result.qty,
            fill=result.fill,
            is_forced=False,
            candle_open_time=signal.candle_open_time,
            clock=clock,
            db=db,
        )
        add_decision(
            db,
            row,
            signal=signal.side.value,
            outcome="approved",
            candle_open_time=signal.candle_open_time,
            reason_code=None,
            reason_message=None,
            fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
            slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
            clock=clock,
        )
        if not result.ok:
            add_decision(
                db,
                row,
                signal=signal.side.value,
                outcome="rejected",
                candle_open_time=signal.candle_open_time,
                reason_code=result.reason_code,
                reason_message=result.reason_message,
                fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
                slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
                clock=clock,
            )
        block_real_session_if_needed(row, result)
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        db.refresh(row)
        if row.state != SessionState.RUNNING.value:
            return
        if row.strategy_fill_count >= row.max_trades:
            await stop_session_async(db, row.id, "max_trades", clock=clock)
            return
        mark2, safe2 = await _quote_mark(row)
        if safe2 and mark2 is not None:
            liq2 = liquidation_equity(
                d(row.cash),
                d(row.position_qty),
                mark2,
                row.position_side,
                d(row.fee_rate),
                d(row.slippage_rate),
            )
            net2 = session_net_pnl(liq2, d(row.starting_capital))
            if net2 is not None:
                if net2 >= d(row.target_net_profit_amount):
                    await stop_session_async(db, row.id, "profit_target", clock=clock)
                elif net2 <= -d(row.max_session_loss_amount):
                    await stop_session_async(db, row.id, "max_loss", clock=clock)
        return

    add_decision(
        db,
        row,
        signal=signal.side.value,
        outcome="rejected",
        candle_open_time=signal.candle_open_time,
        reason_code=result.reason_code,
        reason_message=result.reason_message,
        fast_ema=as_str(signal.fast_ema) if signal.fast_ema is not None else None,
        slow_ema=as_str(signal.slow_ema) if signal.slow_ema is not None else None,
        clock=clock,
    )
    block_real_session_if_needed(row, result)
    row.last_processed_candle_open_time = newest.open_time
    db.commit()
