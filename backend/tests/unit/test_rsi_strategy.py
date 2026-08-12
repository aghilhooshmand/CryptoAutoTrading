"""RSI strategy unit and golden tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.rsi import RsiStrategy
from app.strategy.registry import validate_and_materialize

# Dip below oversold then recover — BUY on recovery crossover at index 27.
_BUY_FIXTURE_PRICES = (
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

_BUY_EXPECTED_SIDES = (
    *["HOLD"] * 27,
    "BUY",
    *["HOLD"] * 3,
)

# Climb into overbought then fall — SELL on recovery crossover at index 44.
_SELL_FIXTURE_PRICES: tuple[str, ...] = tuple(
    str(100 + 3 * i) for i in range(41)
) + tuple(str(100 + 3 * 40 - 5 * (j + 1)) for j in range(15))

_SELL_EXPECTED_SIDES = (
    *["HOLD"] * 44,
    "SELL",
    *["HOLD"] * 11,
)


def _closes(prices: tuple[str, ...], n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(prices[:n])
    ]


def test_warmup_until_period_plus_one():
    s = RsiStrategy(period=14, overbought=70, oversold=30)
    assert s.min_history_candles() == 14
    assert s.evaluate(_closes(_BUY_FIXTURE_PRICES, 14)).reason_code == "warmup"
    assert s.evaluate(_closes(_BUY_FIXTURE_PRICES, 15)).side in {
        SignalSide.BUY,
        SignalSide.SELL,
        SignalSide.HOLD,
    }


def test_locked_fixture_recovery_buy():
    s = RsiStrategy()
    assert len(_BUY_FIXTURE_PRICES) == len(_BUY_EXPECTED_SIDES)
    for n in range(1, len(_BUY_FIXTURE_PRICES) + 1):
        got = s.evaluate(_closes(_BUY_FIXTURE_PRICES, n)).side.value
        assert got == _BUY_EXPECTED_SIDES[n - 1], (
            f"bar {n - 1}: {got} != {_BUY_EXPECTED_SIDES[n - 1]}"
        )


def test_locked_fixture_recovery_sell():
    s = RsiStrategy()
    assert len(_SELL_FIXTURE_PRICES) == len(_SELL_EXPECTED_SIDES)
    for n in range(1, len(_SELL_FIXTURE_PRICES) + 1):
        got = s.evaluate(_closes(_SELL_FIXTURE_PRICES, n)).side.value
        assert got == _SELL_EXPECTED_SIDES[n - 1], (
            f"bar {n - 1}: {got} != {_SELL_EXPECTED_SIDES[n - 1]}"
        )


def test_validate_rejects_oversold_gte_overbought():
    with pytest.raises(Exception) as exc:
        validate_and_materialize(
            "rsi",
            {"period": 14, "overbought": 30, "oversold": 70},
        )
    assert "Oversold threshold must be less than overbought threshold." in str(exc.value)
