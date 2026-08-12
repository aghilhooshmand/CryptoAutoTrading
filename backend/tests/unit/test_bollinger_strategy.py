"""Bollinger Bands strategy unit tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.bollinger import BollingerBandsStrategy
from app.strategy.registry import validate_and_materialize

# period=10 (>5) so population σ × 2 allows closes strictly outside bands.
_BUY_FIXTURE = (
    *["100"] * 15,
    "95",
    "90",
    "85",
    "80",
    "100",
)

_SELL_FIXTURE = (
    *["100"] * 15,
    "105",
    "110",
    "115",
    "120",
    "100",
)


def _closes(prices: tuple[str, ...], n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(prices[:n])
    ]


def test_warmup_until_period_plus_one():
    s = BollingerBandsStrategy(period=10, std_dev="2.0")
    assert s.min_history_candles() == 10
    assert s.evaluate(_closes(_BUY_FIXTURE, 10)).reason_code == "warmup"
    assert s.evaluate(_closes(_BUY_FIXTURE, 11)).side in {
        SignalSide.BUY,
        SignalSide.SELL,
        SignalSide.HOLD,
    }


def test_recovery_buy_after_dip():
    s = BollingerBandsStrategy(period=10, std_dev="2.0")
    sides = [
        s.evaluate(_closes(_BUY_FIXTURE, n)).side
        for n in range(1, len(_BUY_FIXTURE) + 1)
    ]
    assert sides[19] == SignalSide.BUY
    assert sides.count(SignalSide.BUY) == 1


def test_recovery_sell_after_spike():
    s = BollingerBandsStrategy(period=10, std_dev="2.0")
    sides = [
        s.evaluate(_closes(_SELL_FIXTURE, n)).side
        for n in range(1, len(_SELL_FIXTURE) + 1)
    ]
    assert sides[19] == SignalSide.SELL
    assert sides.count(SignalSide.SELL) == 1


def test_hold_while_outside_without_recovering():
    s = BollingerBandsStrategy(period=10, std_dev="2.0")
    # Bars 15–18 stay outside / transitioning without FR-006 recovery BUY.
    for n in range(16, 20):
        assert s.evaluate(_closes(_BUY_FIXTURE, n)).side == SignalSide.HOLD


def test_validate_rejects_stddev_zero():
    with pytest.raises(Exception) as exc:
        validate_and_materialize("bollinger_bands", {"period": 20, "stdDev": "0"})
    assert "must be > 0" in str(exc.value)


def test_stddev_preserved_as_string():
    _, params, _ = validate_and_materialize(
        "bollinger_bands",
        {"period": 20, "stdDev": "2.5"},
    )
    assert params["stdDev"] == "2.5"
