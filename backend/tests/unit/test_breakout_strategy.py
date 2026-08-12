"""Breakout strategy unit tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.breakout import BreakoutStrategy
from app.strategy.registry import validate_and_materialize

_FIXTURE = (
    *["100"] * 12,
    "101",
    "102",
    "103",
    "104",
    "105",
    "106",
    "107",
)

# Every new high after lookback=10 → consecutive BUYs (first at index 12)
_EXPECTED_TAIL = ("HOLD", "BUY", "BUY", "BUY", "BUY", "BUY", "BUY", "BUY")


def _closes(n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(_FIXTURE[:n])
    ]


def test_min_history_is_lookback():
    s = BreakoutStrategy(lookback=10)
    assert s.min_history_candles() == 10
    assert s.evaluate(_closes(10)).reason_code == "warmup"


def test_every_new_extreme_emits_buy():
    s = BreakoutStrategy(lookback=10)
    tail = tuple(
        s.evaluate(_closes(n)).side.value for n in range(len(_FIXTURE) - 7, len(_FIXTURE) + 1)
    )
    assert tail == _EXPECTED_TAIL


def test_hold_inside_range():
    s = BreakoutStrategy(lookback=10)
    flat = [CandleClose(i * 60_000, Decimal("100")) for i in range(15)]
    assert s.evaluate(flat).side == SignalSide.HOLD


def test_validate_rejects_lookback_lt_2():
    with pytest.raises(Exception) as exc:
        validate_and_materialize("breakout", {"lookback": 1})
    assert "lookback" in str(exc.value).lower()
