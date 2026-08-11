"""Shared strategy signal protocol (Simulation + Backtest)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol, Sequence


class SignalSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class CandleClose:
    open_time: int
    close: Decimal


@dataclass(frozen=True)
class StrategySignal:
    side: SignalSide
    candle_open_time: int
    fast_ema: Decimal | None
    slow_ema: Decimal | None
    reason_code: str | None = None


class Strategy(Protocol):
    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal: ...

    def min_history_candles(self) -> int: ...
