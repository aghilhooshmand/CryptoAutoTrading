"""RSI strategy unit and golden tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.rsi import RsiStrategy
from app.strategy.registry import validate_and_materialize

# Dip below oversold then recover — BUY on recovery crossover at index 30 (period=14).
_FIXTURE_PRICES = (
    *["100"] * 16,
    "99",
    "98",
    "97",
    "96",
    "95",
    "94",
    "93",
    "92",
    "91",
    "90",
    "91",
    "93",
    "96",
    "100",
    "105",
)

_EXPECTED_SIDES = (
    *["HOLD"] * 27,
    "BUY",
    *["HOLD"] * 3,
)


def _closes(n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(_FIXTURE_PRICES[:n])
    ]


def test_warmup_until_period_plus_one():
    s = RsiStrategy(period=14, overbought=70, oversold=30)
    assert s.min_history_candles() == 14
    assert s.evaluate(_closes(14)).reason_code == "warmup"
    assert s.evaluate(_closes(15)).side in {SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD}


def test_locked_fixture_recovery_crossover():
    s = RsiStrategy()
    assert len(_FIXTURE_PRICES) == len(_EXPECTED_SIDES)
    for n in range(1, len(_FIXTURE_PRICES) + 1):
        got = s.evaluate(_closes(n)).side.value
        assert got == _EXPECTED_SIDES[n - 1], f"bar {n - 1}: {got} != {_EXPECTED_SIDES[n - 1]}"


def test_validate_rejects_oversold_gte_overbought():
    with pytest.raises(Exception) as exc:
        validate_and_materialize(
            "rsi",
            {"period": 14, "overbought": 30, "oversold": 70},
        )
    assert "Oversold threshold must be less than overbought threshold." in str(exc.value)
