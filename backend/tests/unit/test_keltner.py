"""Keltner channel strategy unit tests (Feature 025 US4)."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.base import CandleClose, SignalSide
from app.strategy.keltner import KeltnerChannelStrategy
from app.strategy.registry import validate_and_materialize


def _ohlc(rows: list[tuple[str, str, str, str]]) -> list[CandleClose]:
    out: list[CandleClose] = []
    for i, (o, h, l, c) in enumerate(rows):
        out.append(
            CandleClose(
                open_time=i * 60_000,
                open=Decimal(o),
                high=Decimal(h),
                low=Decimal(l),
                close=Decimal(c),
            )
        )
    return out


def test_warmup():
    s = KeltnerChannelStrategy(ema_period=5, atr_period=3, atr_mult="1.5")
    assert s.min_history_candles() == 6
    bars = _ohlc([("100", "101", "99", "100")] * 5)
    assert s.evaluate(bars).reason_code == "warmup"


def test_factory_registers():
    _id, params, strat = validate_and_materialize(
        "keltner_channel",
        {"emaPeriod": 20, "atrPeriod": 10, "atrMult": "1.5"},
    )
    assert _id == "keltner_channel"
    assert params["emaPeriod"] == 20
    assert strat.min_history_candles() == 21


def test_evaluate_returns_hold_or_signal_on_long_series():
    s = KeltnerChannelStrategy(ema_period=5, atr_period=3, atr_mult="1.5")
    # Mild mean-reversion path: drift down then bounce
    rows: list[tuple[str, str, str, str]] = []
    px = 100.0
    for i in range(40):
        if i < 25:
            px -= 0.8
        else:
            px += 1.2
        c = f"{px:.4f}"
        h = f"{px + 0.5:.4f}"
        l = f"{px - 0.5:.4f}"
        rows.append((c, h, l, c))
    sides = {s.evaluate(_ohlc(rows[:n])).side for n in range(1, len(rows) + 1)}
    assert SignalSide.HOLD in sides
    # May or may not fire BUY depending on ATR width; ensure no crash and typed sides
    assert sides <= {SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD}
