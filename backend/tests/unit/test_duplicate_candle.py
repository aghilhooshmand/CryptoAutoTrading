"""Duplicate candle and max trades notes covered via pipeline cursor semantics."""

from app.simulation.strategy.dual_ema import DualEmaCrossoverStrategy
from app.simulation.strategy.base import CandleClose, SignalSide
from decimal import Decimal


def test_same_closes_stable_hold_without_cross():
    s = DualEmaCrossoverStrategy(fast=3, slow=5)
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(12)]
    a = s.evaluate(closes)
    b = s.evaluate(closes)
    assert a.side == b.side == SignalSide.HOLD
    assert a.candle_open_time == b.candle_open_time
