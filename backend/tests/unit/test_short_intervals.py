"""Short interval (1m/5m) closed-candle timing for simulation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.models import Candlestick
from app.simulation.pipeline import INTERVAL_SECONDS
from app.simulation.strategy.base import CandleClose
from app.simulation.money import d


def _closed_from_bars(
    candles: list[Candlestick],
    timeframe: str,
    now: datetime,
) -> list[CandleClose]:
    interval = INTERVAL_SECONDS[timeframe]
    now_ms = int(now.timestamp() * 1000)
    closed: list[CandleClose] = []
    for c in candles:
        if c.openTime + interval * 1000 <= now_ms:
            closed.append(CandleClose(open_time=c.openTime, close=d(c.close)))
    return closed


def test_interval_seconds_include_1m_and_5m() -> None:
    assert INTERVAL_SECONDS["1m"] == 60
    assert INTERVAL_SECONDS["5m"] == 300
    assert set(INTERVAL_SECONDS) >= {"1m", "5m", "15m", "1h", "4h", "1d"}


def test_1m_excludes_still_forming_candle() -> None:
    now = datetime(2026, 8, 9, 12, 0, 30, tzinfo=timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    open_closed = now_ms - 60_000
    open_forming = now_ms - 10_000
    bars = [
        Candlestick(
            openTime=open_closed,
            open="100",
            high="101",
            low="99",
            close="100.5",
        ),
        Candlestick(
            openTime=open_forming,
            open="100.5",
            high="102",
            low="100",
            close="101",
        ),
    ]
    closed = _closed_from_bars(bars, "1m", now)
    assert len(closed) == 1
    assert closed[0].open_time == open_closed
    assert closed[0].close == Decimal("100.5")


def test_5m_excludes_still_forming_candle() -> None:
    now = datetime(2026, 8, 9, 12, 3, 0, tzinfo=timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    open_closed = now_ms - 300_000
    open_forming = now_ms - 60_000
    bars = [
        Candlestick(
            openTime=open_closed,
            open="100",
            high="101",
            low="99",
            close="100.2",
        ),
        Candlestick(
            openTime=open_forming,
            open="100.2",
            high="101",
            low="100",
            close="100.8",
        ),
    ]
    closed = _closed_from_bars(bars, "5m", now)
    assert len(closed) == 1
    assert closed[0].open_time == open_closed
