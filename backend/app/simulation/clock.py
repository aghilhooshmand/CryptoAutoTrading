"""Injectable clocks for deterministic session timing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return timezone-aware UTC datetime."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    def __init__(self, initial: datetime | None = None) -> None:
        self._now = initial or datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def set(self, when: datetime) -> None:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        self._now = when

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._now = self._now + timedelta(seconds=seconds)
