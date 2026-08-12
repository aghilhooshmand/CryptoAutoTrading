"""Bollinger Bands strategy unit tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.bollinger import BollingerBandsStrategy
from app.strategy.registry import validate_and_materialize

# Flat then dip below lower band then recover through it (period=5 for short fixture).
_FIXTURE = (
    "100",
    "100",
    "100",
    "100",
    "100",
    "100",
    "100",
    "100",
    "100",
    "95",
    "90",
    "85",
    "92",
    "98",
    "100",
)


def _closes(n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(_FIXTURE[:n])
    ]


def test_warmup_until_period_plus_one():
    s = BollingerBandsStrategy(period=5, std_dev="2.0")
    assert s.min_history_candles() == 5
    assert s.evaluate(_closes(5)).reason_code == "warmup"


def test_recovery_buy_after_dip():
    s = BollingerBandsStrategy(period=5, std_dev="2.0")
    # Find first BUY
    buys = [
        n - 1
        for n in range(1, len(_FIXTURE) + 1)
        if s.evaluate(_closes(n)).side == SignalSide.BUY
    ]
    assert len(buys) >= 1
    assert buys[0] == 10  # recovery through lower band


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
