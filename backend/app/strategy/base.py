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
    """Strategy bar. Existing strategies use ``close``; OHLC optional for range strategies."""

    open_time: int
    close: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None


def bar_open(candle: CandleClose) -> Decimal:
    return candle.open if candle.open is not None else candle.close


def bar_high(candle: CandleClose) -> Decimal:
    return candle.high if candle.high is not None else candle.close


def bar_low(candle: CandleClose) -> Decimal:
    return candle.low if candle.low is not None else candle.close


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
