"""Stochastic strategy unit tests (Feature 025 US4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.registry import validate_and_materialize
from app.strategy.stochastic import StochasticStrategy


def _bars(prices: list[str], *, start: int = 0) -> list[CandleClose]:
    out: list[CandleClose] = []
    for i, p in enumerate(prices):
        px = Decimal(p)
        out.append(
            CandleClose(
                open_time=(start + i) * 60_000,
                open=px,
                high=px,
                low=px,
                close=px,
            )
        )
    return out


def test_warmup_until_k_plus_d():
    s = StochasticStrategy(k_period=5, d_period=3, overbought=80, oversold=20)
    assert s.min_history_candles() == 8
    bars = _bars([str(50 + i) for i in range(7)])
    assert s.evaluate(bars).reason_code == "warmup"


def test_recovery_buy_from_oversold():
    # Drive %K below oversold then recover above — synthetic flat then dip then rise
    prices = ["50"] * 14 + ["40", "35", "30", "28", "32", "38", "45"]
    s = StochasticStrategy(k_period=5, d_period=3, overbought=80, oversold=20)
    sides = [s.evaluate(_bars(prices[:n])).side for n in range(1, len(prices) + 1)]
    assert SignalSide.BUY in sides


def test_validate_rejects_oversold_gte_overbought():
    with pytest.raises(Exception) as exc:
        validate_and_materialize(
            "stochastic",
            {"kPeriod": 14, "dPeriod": 3, "overbought": 20, "oversold": 80},
        )
    assert "Oversold threshold must be less than overbought threshold." in str(exc.value)
