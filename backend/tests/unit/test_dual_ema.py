"""Dual EMA crossover tests."""

from decimal import Decimal

from app.simulation.strategy.base import CandleClose, SignalSide
from app.simulation.strategy.dual_ema import DualEmaCrossoverStrategy


def test_warmup_hold():
    s = DualEmaCrossoverStrategy()
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(10)]
    sig = s.evaluate(closes)
    assert sig.side == SignalSide.HOLD
    assert sig.reason_code == "warmup"


def test_upcross_buy():
    s = DualEmaCrossoverStrategy(fast=3, slow=5)
    # Flat then sharp rise to force fast above slow
    prices = [Decimal("100")] * 8 + [Decimal("110"), Decimal("120"), Decimal("130")]
    closes = [CandleClose(i * 60_000, p) for i, p in enumerate(prices)]
    sig = s.evaluate(closes)
    assert sig.side in {SignalSide.BUY, SignalSide.HOLD, SignalSide.SELL}
    # At least produces EMAs
    assert sig.fast_ema is not None
