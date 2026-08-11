"""Closed-candle pipeline: market data → strategy → control → risk → execution."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.market_data.models import MarketStatus
from app.market_data.service import get_market_data_service
from app.simulation.accounting import liquidation_equity, session_net_pnl
from app.simulation.clock import Clock
from app.simulation.control.controller import TradingController
from app.simulation.control.risk import UNSAFE_QUOTE_LIMIT, RiskContext, RiskManager
from app.simulation.execution.port import ExecutionIntent, SimulationExecutionEngine
from app.simulation.money import as_str, d
from app.simulation.session_service import (
    _apply_fill,
    add_decision,
    stop_session_async,
)
from app.simulation.state_machine import SessionState
from app.simulation.strategy.base import CandleClose, SignalSide
from app.simulation.strategy.dual_ema import DualEmaCrossoverStrategy

INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}



async def _closed_candles(symbol: str, timeframe: str, clock: Clock) -> list[CandleClose]:
    series = await get_market_data_service().get_candles(symbol, timeframe)
    interval = INTERVAL_SECONDS[timeframe]
    now_ms = int(clock.now().timestamp() * 1000)
    closed: list[CandleClose] = []
    for c in series.candles:
        if c.openTime + interval * 1000 <= now_ms:
            closed.append(CandleClose(open_time=c.openTime, close=d(c.close)))
    return closed


async def _quote_mark(symbol: str) -> tuple[Decimal | None, bool]:
    try:
        quote = await get_market_data_service().get_quote(symbol)
    except Exception:  # noqa: BLE001
        return None, False
    if quote.status != MarketStatus.FRESH:
        return None, False
    return d(quote.lastPrice), True


async def process_session_tick(db: Session, row: SimulationSessionRow, clock: Clock) -> None:
    if row.state != SessionState.RUNNING.value:
        return

    if row.started_at is not None:
        elapsed = (clock.now() - row.started_at).total_seconds()
        if elapsed >= row.duration_seconds:
            await stop_session_async(db, row.id, "duration_elapsed", clock=clock)
            return

    mark, safe = await _quote_mark(row.symbol)
    if not safe:
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
        closes = await _closed_candles(row.symbol, row.timeframe, clock)
    except Exception:  # noqa: BLE001
        row.unsafe_quote_streak += 1
        db.commit()
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

    strategy = DualEmaCrossoverStrategy()
    signal = strategy.evaluate(closes)
    controller = TradingController()
    risk = RiskManager()
    engine = SimulationExecutionEngine()

    ctrl = controller.review(SessionState(row.state), signal)
    if signal.side == SignalSide.HOLD:
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

    rctx = RiskContext(
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

    assert mark is not None
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
    if not result.ok or result.fill is None or result.qty is None:
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
        row.last_processed_candle_open_time = newest.open_time
        db.commit()
        return

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
    row.last_processed_candle_open_time = newest.open_time
    db.commit()

    db.refresh(row)
    if row.strategy_fill_count >= row.max_trades:
        await stop_session_async(db, row.id, "max_trades", clock=clock)
        return
    mark2, safe2 = await _quote_mark(row.symbol)
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
