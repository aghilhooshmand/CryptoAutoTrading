"""Dual EMA continuity: defaults 9/21 match pre-migration signal semantics (SC-003)."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.base import CandleClose, SignalSide
from app.strategy.dual_ema import DualEmaCrossoverStrategy

# Fixed closed-candle closes (USDT). Locked golden sequence for Dual EMA(9/21).
# Warm-up HOLD through index 21 (need S+1=22 bars); BUY on first rise; SELL on decline.
_FIXTURE_PRICES = (
    # 0..21 flat — warm-up
    *["100"] * 22,
    # rising — upcross BUY at first post-warm-up bar
    "101",
    "103",
    "106",
    "110",
    "115",
    "120",
    "125",
    "130",
    # flat high
    *["130"] * 5,
    # falling — downcross SELL
    "128",
    "124",
    "118",
    "110",
    "100",
    "90",
    "80",
    # flat low
    *["80"] * 5,
)

# Expected side per evaluate(closes[:n]) for n=1..len (index = n-1).
_EXPECTED_SIDES = (
    *["HOLD"] * 22,
    "BUY",
    *["HOLD"] * 17,
    "SELL",
    *["HOLD"] * 6,
)


def _fixture_closes(n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(_FIXTURE_PRICES[:n])
    ]


def test_warmup_hold_defaults():
    s = DualEmaCrossoverStrategy()
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(10)]
    sig = s.evaluate(closes)
    assert sig.side == SignalSide.HOLD
    assert sig.reason_code == "warmup"


def test_warmup_until_s_plus_one():
    s = DualEmaCrossoverStrategy(fast=3, slow=5)
    closes = [CandleClose(i * 1000, Decimal("100")) for i in range(5)]
    assert s.evaluate(closes).reason_code == "warmup"
    closes.append(CandleClose(5 * 1000, Decimal("100")))
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


def test_locked_fixture_signal_sequence_defaults_9_21():
    """SC-003: fixed fixture → locked BUY/SELL/HOLD sequence for Dual EMA 9/21."""
    assert len(_FIXTURE_PRICES) == len(_EXPECTED_SIDES)
    s = DualEmaCrossoverStrategy()  # defaults 9/21
    actual = []
    for n in range(1, len(_FIXTURE_PRICES) + 1):
        sig = s.evaluate(_fixture_closes(n))
        actual.append(sig.side.value)
    assert actual == list(_EXPECTED_SIDES)
    assert actual[21] == "HOLD"
    assert actual[22] == "BUY"
    assert actual[40] == "SELL"


def test_locked_fixture_matches_explicit_9_21():
    """Same golden sequence whether constructed as default or explicit 9/21."""
    a = DualEmaCrossoverStrategy()
    b = DualEmaCrossoverStrategy(fast=9, slow=21)
    for n in range(1, len(_FIXTURE_PRICES) + 1):
        closes = _fixture_closes(n)
        assert a.evaluate(closes).side == b.evaluate(closes).side
