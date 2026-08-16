"""Chronological Dual EMA backtest engine (Feature 004)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.backtest import repository as repo
from app.backtest.execution import HistoricalExecutionAdapter
from app.backtest.metrics import buy_and_hold, equity_point, max_drawdown, summarize_round_trips
from app.execution.tpsl import derive_levels, evaluate_triggers
from app.market_data.models import Candlestick
from app.simulation.control.controller import TradingController
from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d, quantize_money
from app.simulation.state_machine import SessionState
from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.registry import build_from_stored

# Sentinels when optional early-exit / max_trades omitted
_HUGE = Decimal("1000000000000")
_HUGE_TRADES = 10**9


@dataclass
class EngineState:
    cash: Decimal
    position_side: str = "flat"
    position_qty: Decimal = Decimal("0")
    entry_cost_basis: Decimal = Decimal("0")
    strategy_fill_count: int = 0
    trade_count: int = 0
    total_fees: Decimal = Decimal("0")
    total_slippage: Decimal = Decimal("0")
    open_round_trip_id: str | None = None
    open_entry_cash_out: Decimal = Decimal("0")
    round_trip_pnls: list[Decimal] = field(default_factory=list)
    equity_series: list[Decimal] = field(default_factory=list)
    processed_open_times: set[int] = field(default_factory=set)
    stop_strategy: bool = False
    # Feature 025 protective TP/SL
    take_profit_percent: Decimal | None = None
    stop_loss_percent: Decimal | None = None
    take_profit_price: Decimal | None = None
    stop_loss_price: Decimal | None = None
    entry_fill_candle_open_time: int | None = None


def run_engine(
    db: Session,
    run_id: str,
    candles: list[Candlestick],
    *,
    starting_capital: Decimal,
    allocated_capital: Decimal,
    max_position_size: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
    max_trades: int | None,
    target_net_profit_amount: Decimal | None,
    max_session_loss_amount: Decimal | None,
    wire_shared: bool = True,
    strategy_id: str = "dual_ema",
    strategy_params: dict[str, Any] | None = None,
    take_profit_percent: Decimal | None = None,
    stop_loss_percent: Decimal | None = None,
) -> dict[str, Any]:
    """
    Process candles. When wire_shared is False (T020 skeleton), only walks candles
    and records HOLD stubs without Dual EMA/control/risk fills.
    """
    state = EngineState(
        cash=starting_capital,
        take_profit_percent=take_profit_percent,
        stop_loss_percent=stop_loss_percent,
    )
    adapter = HistoricalExecutionAdapter()
    strategy = (
        build_from_stored(strategy_id, strategy_params) if wire_shared else None
    )
    controller = TradingController() if wire_shared else None
    risk = RiskManager() if wire_shared else None
    closes: list[CandleClose] = []

    eff_max_trades = max_trades if max_trades is not None else _HUGE_TRADES
    eff_profit = target_net_profit_amount if target_net_profit_amount is not None else _HUGE
    eff_loss = max_session_loss_amount if max_session_loss_amount is not None else _HUGE

    for i, candle in enumerate(candles):
        if candle.openTime in state.processed_open_times:
            continue
        state.processed_open_times.add(candle.openTime)
        close_px = d(candle.close)
        closes.append(
            CandleClose(
                open_time=candle.openTime,
                close=close_px,
                open=d(candle.open),
                high=d(candle.high),
                low=d(candle.low),
            )
        )

        if not wire_shared or strategy is None or controller is None or risk is None:
            repo.add_decision(
                db,
                run_id,
                signal="HOLD",
                outcome="hold",
                candle_open_time=candle.openTime,
                reason_code="skeleton",
                reason_message="Engine skeleton; shared wiring pending",
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        # Feature 025: protective TP/SL after session hard-stops path, before strategy.
        # Protective SELL must still pass Controller → Risk → Execution (FR-003).
        if state.position_side == "long" and (
            state.take_profit_price is not None or state.stop_loss_price is not None
        ):
            protective = evaluate_triggers(
                candle_open_time=candle.openTime,
                high=d(candle.high),
                low=d(candle.low),
                entry_fill_candle_open_time=state.entry_fill_candle_open_time,
                tp_price=state.take_profit_price,
                sl_price=state.stop_loss_price,
            )
            if protective is not None:
                protective_signal = StrategySignal(
                    side=SignalSide.SELL,
                    candle_open_time=candle.openTime,
                    fast_ema=None,
                    slow_ema=None,
                    reason_code=protective,
                )
                ctrl = controller.review(SessionState.RUNNING, protective_signal)
                if not ctrl.approved:
                    repo.add_decision(
                        db,
                        run_id,
                        signal="SELL",
                        outcome="rejected",
                        candle_open_time=candle.openTime,
                        reason_code=ctrl.reason_code,
                        reason_message=ctrl.reason_message,
                    )
                    state.equity_series.append(
                        equity_point(
                            state.cash,
                            state.position_qty,
                            state.position_side,
                            close_px,
                            fee_rate,
                            slippage_rate,
                        )
                    )
                    continue

                ctx = RiskContext(
                    position_side=state.position_side,
                    cash=state.cash,
                    qty=state.position_qty,
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                    start_equity=starting_capital,
                    target_net_profit_amount=eff_profit,
                    max_session_loss_amount=eff_loss,
                    strategy_fill_count=state.strategy_fill_count,
                    max_trades=eff_max_trades,
                    mark_price=close_px,
                    mark_safe=True,
                )
                risk_dec = risk.review(protective_signal, ctx)
                # Session/emergency hard-stops from Risk take precedence over TP/SL (FR-006).
                if risk_dec.trigger_stop:
                    if state.position_side == "long":
                        _flatten(
                            db,
                            run_id,
                            state,
                            adapter,
                            reference=close_px,
                            fill_open_time=candle.openTime,
                            fee_rate=fee_rate,
                            slippage_rate=slippage_rate,
                            forced=True,
                            end_of_run=False,
                            reason=risk_dec.trigger_stop,
                        )
                    state.stop_strategy = True
                    repo.add_decision(
                        db,
                        run_id,
                        signal="SELL",
                        outcome="rejected",
                        candle_open_time=candle.openTime,
                        reason_code=risk_dec.reason_code,
                        reason_message=risk_dec.reason_message,
                    )
                    state.equity_series.append(
                        equity_point(
                            state.cash,
                            state.position_qty,
                            state.position_side,
                            close_px,
                            fee_rate,
                            slippage_rate,
                        )
                    )
                    continue
                if not risk_dec.approved:
                    repo.add_decision(
                        db,
                        run_id,
                        signal="SELL",
                        outcome="rejected",
                        candle_open_time=candle.openTime,
                        reason_code=risk_dec.reason_code,
                        reason_message=risk_dec.reason_message,
                    )
                    state.equity_series.append(
                        equity_point(
                            state.cash,
                            state.position_qty,
                            state.position_side,
                            close_px,
                            fee_rate,
                            slippage_rate,
                        )
                    )
                    continue

                if i + 1 >= len(candles):
                    repo.add_decision(
                        db,
                        run_id,
                        signal="SELL",
                        outcome="approved_unexecutable",
                        candle_open_time=candle.openTime,
                        reason_code="no_next_candle",
                        reason_message=(
                            f"Protective {protective} triggered but no next candle open for fill"
                        ),
                    )
                    state.equity_series.append(
                        equity_point(
                            state.cash,
                            state.position_qty,
                            state.position_side,
                            close_px,
                            fee_rate,
                            slippage_rate,
                        )
                    )
                    continue
                next_c = candles[i + 1]
                _flatten(
                    db,
                    run_id,
                    state,
                    adapter,
                    reference=d(next_c.open),
                    fill_open_time=next_c.openTime,
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                    forced=True,
                    end_of_run=False,
                    reason=protective,
                )
                state.equity_series.append(
                    equity_point(
                        state.cash,
                        state.position_qty,
                        state.position_side,
                        close_px,
                        fee_rate,
                        slippage_rate,
                    )
                )
                continue

        signal = strategy.evaluate(closes)
        fast = as_str(signal.fast_ema) if signal.fast_ema is not None else None
        slow = as_str(signal.slow_ema) if signal.slow_ema is not None else None

        if state.stop_strategy or signal.side == SignalSide.HOLD:
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="hold",
                candle_open_time=candle.openTime,
                reason_code=signal.reason_code,
                reason_message=None,
                fast_ema=fast,
                slow_ema=slow,
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        ctrl = controller.review(SessionState.RUNNING, signal)
        if not ctrl.approved:
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="rejected",
                candle_open_time=candle.openTime,
                reason_code=ctrl.reason_code,
                reason_message=ctrl.reason_message,
                fast_ema=fast,
                slow_ema=slow,
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        ctx = RiskContext(
            position_side=state.position_side,
            cash=state.cash,
            qty=state.position_qty,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            start_equity=starting_capital,
            target_net_profit_amount=eff_profit,
            max_session_loss_amount=eff_loss,
            strategy_fill_count=state.strategy_fill_count,
            max_trades=eff_max_trades,
            mark_price=close_px,
            mark_safe=True,
        )
        risk_dec = risk.review(signal, ctx)
        if risk_dec.trigger_stop:
            # Flatten if long then stop further strategy entries
            if state.position_side == "long":
                _flatten(
                    db,
                    run_id,
                    state,
                    adapter,
                    reference=close_px,
                    fill_open_time=candle.openTime,
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                    forced=True,
                    end_of_run=False,
                    reason=risk_dec.trigger_stop,
                )
            state.stop_strategy = True
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="rejected",
                candle_open_time=candle.openTime,
                reason_code=risk_dec.reason_code,
                reason_message=risk_dec.reason_message,
                fast_ema=fast,
                slow_ema=slow,
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        if not risk_dec.approved:
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="rejected",
                candle_open_time=candle.openTime,
                reason_code=risk_dec.reason_code,
                reason_message=risk_dec.reason_message,
                fast_ema=fast,
                slow_ema=slow,
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        # Need next candle for strategy fill
        if i + 1 >= len(candles):
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="approved_unexecutable",
                candle_open_time=candle.openTime,
                reason_code="no_next_candle",
                reason_message="Approved by risk but no next candle open for fill",
                fast_ema=fast,
                slow_ema=slow,
            )
            state.equity_series.append(
                equity_point(
                    state.cash,
                    state.position_qty,
                    state.position_side,
                    close_px,
                    fee_rate,
                    slippage_rate,
                )
            )
            continue

        next_c = candles[i + 1]
        ref = d(next_c.open)
        if signal.side == SignalSide.BUY:
            result = adapter.buy(
                reference_price=ref,
                cash=state.cash,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
                allocated_capital=allocated_capital,
                max_position_size=max_position_size,
                position_side=state.position_side,
            )
        else:
            result = adapter.sell(
                reference_price=ref,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
                position_side=state.position_side,
                position_qty=state.position_qty,
            )

        if not result.ok or result.fill is None or result.qty is None:
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="rejected",
                candle_open_time=candle.openTime,
                reason_code=result.reason_code,
                reason_message=result.reason_message,
                fast_ema=fast,
                slow_ema=slow,
            )
        else:
            _apply_strategy_fill(
                db,
                run_id,
                state,
                side=signal.side.value,
                qty=result.qty,
                fill=result.fill,
                signal_open=candle.openTime,
                fill_open=next_c.openTime,
            )
            repo.add_decision(
                db,
                run_id,
                signal=signal.side.value,
                outcome="approved",
                candle_open_time=candle.openTime,
                fast_ema=fast,
                slow_ema=slow,
            )

        state.equity_series.append(
            equity_point(
                state.cash,
                state.position_qty,
                state.position_side,
                close_px,
                fee_rate,
                slippage_rate,
            )
        )

    # End-of-run flatten
    if candles and state.position_side == "long":
        last = candles[-1]
        _flatten(
            db,
            run_id,
            state,
            adapter,
            reference=d(last.close),
            fill_open_time=last.openTime,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            forced=True,
            end_of_run=True,
            reason="end_of_run_flatten",
        )
        state.equity_series.append(
            equity_point(
                state.cash,
                state.position_qty,
                state.position_side,
                d(last.close),
                fee_rate,
                slippage_rate,
            )
        )

    db.commit()

    ending = state.cash
    net_pnl = quantize_money(ending - starting_capital)
    ret = quantize_money(net_pnl / starting_capital) if starting_capital > 0 else Decimal("0")
    dd_abs, dd_pct = max_drawdown(state.equity_series)
    bh_net, bh_ret = buy_and_hold(
        candles,
        starting_capital=starting_capital,
        allocated_capital=allocated_capital,
        max_position_size=max_position_size,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )
    rt = summarize_round_trips(state.round_trip_pnls)
    return {
        "startingCapital": as_str(starting_capital),
        "endingCapital": as_str(ending),
        "netPnl": as_str(net_pnl),
        "returnPct": as_str(ret),
        "tradeCount": state.trade_count,
        "roundTripCount": rt["roundTripCount"],
        "winningTrades": rt["winningTrades"],
        "losingTrades": rt["losingTrades"],
        "winRate": rt["winRate"],
        "totalFees": as_str(state.total_fees),
        "totalSlippage": as_str(state.total_slippage),
        "maxDrawdown": as_str(dd_abs),
        "maxDrawdownPct": as_str(dd_pct),
        "bestTrade": rt["bestTrade"],
        "worstTrade": rt["worstTrade"],
        "buyAndHoldNetPnl": as_str(bh_net),
        "buyAndHoldReturnPct": as_str(bh_ret),
        "strategyFillCount": state.strategy_fill_count,
    }


def _clear_protective(state: EngineState) -> None:
    state.take_profit_price = None
    state.stop_loss_price = None
    state.entry_fill_candle_open_time = None


def _apply_strategy_fill(
    db: Session,
    run_id: str,
    state: EngineState,
    *,
    side: str,
    qty: Decimal,
    fill,
    signal_open: int,
    fill_open: int,
) -> None:
    state.cash = quantize_money(state.cash + fill.cash_delta)
    state.total_fees += fill.fee
    state.total_slippage += fill.slippage_cost
    state.trade_count += 1
    state.strategy_fill_count += 1
    if side == "BUY":
        rt_id = str(uuid.uuid4())
        state.open_round_trip_id = rt_id
        state.open_entry_cash_out = -fill.cash_delta
        state.position_side = "long"
        state.position_qty = qty
        state.entry_cost_basis = -fill.cash_delta
        tp_price, sl_price = derive_levels(
            fill.fill_price,
            state.take_profit_percent,
            state.stop_loss_percent,
        )
        state.take_profit_price = tp_price
        state.stop_loss_price = sl_price
        state.entry_fill_candle_open_time = fill_open
        repo.add_trade(
            db,
            run_id,
            side="BUY",
            qty=as_str(qty),
            reference_price=as_str(fill.reference_price),
            fill_price=as_str(fill.fill_price),
            fee=as_str(fill.fee),
            slippage_cost=as_str(fill.slippage_cost),
            notional=as_str(fill.notional),
            signal_candle_open_time=signal_open,
            fill_candle_open_time=fill_open,
            round_trip_id=rt_id,
        )
    else:
        rt_id = state.open_round_trip_id
        # Round-trip net ≈ entry cash outlay recovered via sell cash_delta
        pnl = quantize_money(fill.cash_delta - state.open_entry_cash_out)
        state.round_trip_pnls.append(pnl)
        state.position_side = "flat"
        state.position_qty = Decimal("0")
        state.open_round_trip_id = None
        state.open_entry_cash_out = Decimal("0")
        _clear_protective(state)
        repo.add_trade(
            db,
            run_id,
            side="SELL",
            qty=as_str(qty),
            reference_price=as_str(fill.reference_price),
            fill_price=as_str(fill.fill_price),
            fee=as_str(fill.fee),
            slippage_cost=as_str(fill.slippage_cost),
            notional=as_str(fill.notional),
            signal_candle_open_time=signal_open,
            fill_candle_open_time=fill_open,
            round_trip_id=rt_id,
        )


def _flatten(
    db: Session,
    run_id: str,
    state: EngineState,
    adapter: HistoricalExecutionAdapter,
    *,
    reference: Decimal,
    fill_open_time: int,
    fee_rate: Decimal,
    slippage_rate: Decimal,
    forced: bool,
    end_of_run: bool,
    reason: str,
) -> None:
    result = adapter.sell(
        reference_price=reference,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        position_side=state.position_side,
        position_qty=state.position_qty,
    )
    if not result.ok or result.fill is None or result.qty is None:
        return
    fill = result.fill
    state.cash = quantize_money(state.cash + fill.cash_delta)
    state.total_fees += fill.fee
    state.total_slippage += fill.slippage_cost
    state.trade_count += 1
    pnl = quantize_money(fill.cash_delta - state.open_entry_cash_out)
    state.round_trip_pnls.append(pnl)
    rt_id = state.open_round_trip_id
    state.position_side = "flat"
    state.position_qty = Decimal("0")
    state.open_round_trip_id = None
    state.open_entry_cash_out = Decimal("0")
    _clear_protective(state)
    repo.add_trade(
        db,
        run_id,
        side="SELL",
        qty=as_str(result.qty),
        reference_price=as_str(fill.reference_price),
        fill_price=as_str(fill.fill_price),
        fee=as_str(fill.fee),
        slippage_cost=as_str(fill.slippage_cost),
        notional=as_str(fill.notional),
        signal_candle_open_time=None,
        fill_candle_open_time=fill_open_time,
        is_end_of_run_flatten=end_of_run,
        is_forced_close=forced,
        round_trip_id=rt_id,
    )
    repo.add_decision(
        db,
        run_id,
        signal="SELL",
        outcome="forced",
        candle_open_time=fill_open_time,
        reason_code=reason,
        reason_message="Forced or end-of-run flatten",
    )
