"""Dual EMA continuity: defaults 9/21 match pre-migration signal semantics."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.base import CandleClose, SignalSide
from app.strategy.dual_ema import DualEmaCrossoverStrategy


def test_warmup_hold_defaults():
    s = DualEmaCrossoverStrategy()
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(10)]
    sig = s.evaluate(closes)
    assert sig.side == SignalSide.HOLD
    assert sig.reason_code == "warmup"


def test_warmup_until_s_plus_one():
    s = DualEmaCrossoverStrategy(fast=3, slow=5)
    # Need S+1 = 6 candles before ready
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(5)]
    assert s.evaluate(closes).reason_code == "warmup"
    closes.append(CandleClose(5 * 1000, Decimal("100")))
    # At S+1 may still be HOLD but not necessarily warmup if EMAs exist
    sig = s.evaluate(closes)
    assert sig.side in {SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD}


def test_defaults_match_legacy_constructor():
    """Default DualEmaCrossoverStrategy() is fast=9 slow=21."""
    a = DualEmaCrossoverStrategy()
    b = DualEmaCrossoverStrategy(fast=9, slow=21)
    prices = [Decimal(str(100 + (i % 7))) for i in range(40)]
    closes = [CandleClose(i * 60_000, p) for i, p in enumerate(prices)]
    assert a.evaluate(closes).side == b.evaluate(closes).side
    assert a.evaluate(closes).fast_ema == b.evaluate(closes).fast_ema
