"""Unit tests for shared strategy indicator helpers."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.dual_ema import DualEmaCrossoverStrategy
from app.strategy.indicators import (
    ema_series,
    population_stdev_series,
    sma_series,
    wilder_rsi_series,
)


def test_ema_seed_matches_dual_ema_style():
    values = [Decimal(str(100 + i)) for i in range(30)]
    shared = ema_series(values, 9)
    legacy = DualEmaCrossoverStrategy(fast=9, slow=21)
    # Reuse dual_ema private _ema via evaluate path — compare first seeded EMA point
    from app.strategy import dual_ema as de

    local = de._ema(values, 9)
    assert shared[8] == local[8]
    assert shared[-1] == local[-1]


def test_sma_computes_window_mean():
    values = [Decimal(str(i)) for i in range(1, 11)]
    sma = sma_series(values, 3)
    assert sma[2] == Decimal("2")
    assert sma[-1] == Decimal("9")


def test_population_stdev_flat_window_is_zero():
    values = [Decimal("100")] * 10
    st = population_stdev_series(values, 5)
    assert st[4] == Decimal("0")


def test_wilder_rsi_warmup_nones():
    values = [Decimal("100")] * 20
    rsi = wilder_rsi_series(values, 14)
    assert all(x is None for x in rsi[:14])
    assert rsi[14] is not None
