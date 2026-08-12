"""MACD strategy unit tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.strategy.base import CandleClose, SignalSide
from app.strategy.macd import MacdStrategy
from app.strategy.registry import validate_and_materialize


def _oscillating_prices(n: int = 80) -> tuple[str, ...]:
    out: list[str] = []
    for i in range(n):
        base = 100 + (10 if (i // 8) % 2 == 0 else -10)
        out.append(str(base + (i % 8)))
    return tuple(out)


_FIXTURE = _oscillating_prices(80)
# Non-HOLD events at these bar indices (0-based evaluate index)
_EXPECTED_EVENTS = {41: "SELL", 48: "BUY", 57: "SELL", 65: "BUY", 73: "SELL"}


def _closes(n: int) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p))
        for i, p in enumerate(_FIXTURE[:n])
    ]


def test_min_history_slow_plus_signal():
    s = MacdStrategy(fast=12, slow=26, signal=9)
    assert s.min_history_candles() == 35


def test_warmup_before_s_plus_one():
    s = MacdStrategy()
    assert s.evaluate(_closes(35)).reason_code == "warmup"


def test_crossover_events_on_fixture():
    s = MacdStrategy()
    seen: dict[int, str] = {}
    for n in range(1, len(_FIXTURE) + 1):
        side = s.evaluate(_closes(n)).side.value
        if side != "HOLD":
            seen[n - 1] = side
    assert seen == _EXPECTED_EVENTS


def test_validate_rejects_fast_gte_slow():
    with pytest.raises(Exception) as exc:
        validate_and_materialize("macd", {"fastPeriod": 26, "slowPeriod": 12, "signalPeriod": 9})
    assert "Fast period must be less than slow period." in str(exc.value)
