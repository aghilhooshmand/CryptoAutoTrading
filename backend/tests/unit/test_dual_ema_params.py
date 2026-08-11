"""Dual EMA non-default period behavior."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.base import CandleClose, SignalSide
from app.strategy.dual_ema import DualEmaCrossoverStrategy
from app.strategy.registry import validate_and_materialize


def test_non_default_periods_change_warmup():
    s = DualEmaCrossoverStrategy(fast=5, slow=10)
    assert s.min_history_candles() == 10
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(10)]
    assert s.evaluate(closes).reason_code == "warmup"
    closes.append(CandleClose(10_000, Decimal("100")))
    sig = s.evaluate(closes)
    assert sig.side in {SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD}


def test_materialize_uses_submitted_periods_not_forced_921():
    _, params, inst = validate_and_materialize(
        "dual_ema", {"fastPeriod": 5, "slowPeriod": 20}
    )
    assert params == {"fastPeriod": 5, "slowPeriod": 20}
    assert inst.fast == 5
    assert inst.slow == 20
