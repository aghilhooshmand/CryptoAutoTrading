"""Backtest history size limits (Feature 004)."""

from __future__ import annotations

from app.market_data.models import ALLOWED_INTERVALS

MAX_BACKTEST_CANDLES = 5000
MIN_BACKTEST_CANDLES = 21  # Dual EMA slow period

INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def interval_ms(interval: str) -> int:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    return INTERVAL_MS[interval]


def estimate_candle_count(start_ms: int, end_ms: int, interval: str) -> int:
    if end_ms <= start_ms:
        return 0
    step = interval_ms(interval)
    return max(0, (end_ms - start_ms) // step)


def is_oversized_estimate(start_ms: int, end_ms: int, interval: str) -> bool:
    return estimate_candle_count(start_ms, end_ms, interval) > MAX_BACKTEST_CANDLES


def is_oversized_count(count: int) -> bool:
    return count > MAX_BACKTEST_CANDLES


def is_insufficient_count(count: int, min_candles: int = MIN_BACKTEST_CANDLES) -> bool:
    return count < min_candles


def assert_supported_interval(interval: str) -> None:
    if interval not in ALLOWED_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")
