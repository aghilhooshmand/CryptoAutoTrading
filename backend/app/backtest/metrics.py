"""Backtest metrics: equity drawdown, round-trips, buy-and-hold."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.market_data.models import Candlestick
from app.simulation.accounting import buy_fill, liquidation_equity, qty_from_notional, sell_fill
from app.simulation.money import as_str, d, quantize_money
from app.simulation.position_sizing import intended_notional


def max_drawdown(equity_series: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    if not equity_series:
        return Decimal("0"), Decimal("0")
    peak = equity_series[0]
    max_dd = Decimal("0")
    max_dd_pct = Decimal("0")
    for eq in equity_series:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak) if peak > 0 else Decimal("0")
    return quantize_money(max_dd), quantize_money(max_dd_pct)


def buy_and_hold(
    candles: Sequence[Candlestick],
    *,
    starting_capital: Decimal,
    allocated_capital: Decimal,
    max_position_size: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> tuple[Decimal, Decimal]:
    if not candles:
        return Decimal("0"), Decimal("0")
    if len(candles) >= 2:
        entry_ref = d(candles[1].open)
    else:
        entry_ref = d(candles[0].close)
    exit_ref = d(candles[-1].close)
    target = intended_notional(
        starting_capital, fee_rate, allocated_capital, max_position_size
    )
    provisional = buy_fill(Decimal("1"), entry_ref, fee_rate, slippage_rate)
    qty = qty_from_notional(target, provisional.fill_price)
    if qty <= 0:
        return Decimal("0"), Decimal("0")
    entry = buy_fill(qty, entry_ref, fee_rate, slippage_rate)
    exit_fill = sell_fill(qty, exit_ref, fee_rate, slippage_rate)
    net = quantize_money(entry.cash_delta + exit_fill.cash_delta)
    ret = quantize_money(net / starting_capital) if starting_capital > 0 else Decimal("0")
    return net, ret


def summarize_round_trips(
    round_trip_pnls: Sequence[Decimal],
) -> dict[str, str | int | None]:
    wins = sum(1 for p in round_trip_pnls if p > 0)
    losses = sum(1 for p in round_trip_pnls if p <= 0)
    n = len(round_trip_pnls)
    win_rate = quantize_money(Decimal(wins) / Decimal(n)) if n else Decimal("0")
    best = max(round_trip_pnls) if round_trip_pnls else None
    worst = min(round_trip_pnls) if round_trip_pnls else None
    return {
        "roundTripCount": n,
        "winningTrades": wins,
        "losingTrades": losses,
        "winRate": as_str(win_rate),
        "bestTrade": as_str(best) if best is not None else None,
        "worstTrade": as_str(worst) if worst is not None else None,
    }


def equity_point(
    cash: Decimal,
    qty: Decimal,
    side: str,
    mark: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> Decimal:
    eq = liquidation_equity(cash, qty, mark, side, fee_rate, slippage_rate)
    return quantize_money(eq if eq is not None else cash)
