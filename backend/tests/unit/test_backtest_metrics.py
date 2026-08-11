"""Unit tests for backtest metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.backtest.metrics import buy_and_hold, max_drawdown
from app.market_data.models import CandleInterval, Candlestick


def test_max_drawdown_peak_to_trough():
    series = [Decimal("100"), Decimal("120"), Decimal("90"), Decimal("95")]
    dd, pct = max_drawdown(series)
    assert dd == Decimal("30")
    assert pct == Decimal("0.25")


def test_buy_and_hold_uses_second_open_independent_of_warmup():
    candles = [
        Candlestick(openTime=1, open="100", high="101", low="99", close="100"),
        Candlestick(openTime=2, open="105", high="106", low="104", close="105"),
        Candlestick(openTime=3, open="110", high="111", low="109", close="108"),
    ]
    net, ret = buy_and_hold(
        candles,
        starting_capital=Decimal("1000"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )
    # Entry at 105 open, exit at 108 close, full capital → positive
    assert net > 0
    assert ret > 0
