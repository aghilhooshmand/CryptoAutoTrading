"""Unit tests for backtest history limits."""

from __future__ import annotations

from app.backtest.limits import (
    MAX_BACKTEST_CANDLES,
    MIN_BACKTEST_CANDLES,
    estimate_candle_count,
    is_insufficient_count,
    is_oversized_count,
    is_oversized_estimate,
)


def test_oversized_estimate():
    # 5001 hours
    start = 0
    end = 5001 * 3_600_000
    assert estimate_candle_count(start, end, "1h") == 5001
    assert is_oversized_estimate(start, end, "1h")


def test_not_oversized_at_cap():
    start = 0
    end = MAX_BACKTEST_CANDLES * 3_600_000
    assert estimate_candle_count(start, end, "1h") == MAX_BACKTEST_CANDLES
    assert not is_oversized_estimate(start, end, "1h")


def test_insufficient_counts():
    assert is_insufficient_count(0)
    assert is_insufficient_count(20)
    assert not is_insufficient_count(MIN_BACKTEST_CANDLES)
    assert is_oversized_count(MAX_BACKTEST_CANDLES + 1)
    assert not is_oversized_count(MAX_BACKTEST_CANDLES)
