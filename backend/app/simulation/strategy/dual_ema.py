"""Dual EMA(9)/EMA(21) crossover on closed candle closes."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.simulation.money import quantize_money
from app.simulation.strategy.base import CandleClose, SignalSide, StrategySignal


def _ema(values: list[Decimal], period: int) -> list[Decimal | None]:
    if len(values) < period:
        return [None] * len(values)
    out: list[Decimal | None] = [None] * len(values)
    seed = sum(values[:period], Decimal("0")) / Decimal(period)
    out[period - 1] = quantize_money(seed)
    k = Decimal("2") / (Decimal(period) + Decimal("1"))
    prev = out[period - 1]
    assert prev is not None
    for i in range(period, len(values)):
        prev = quantize_money(values[i] * k + prev * (Decimal("1") - k))
        out[i] = prev
    return out


class DualEmaCrossoverStrategy:
    def __init__(self, fast: int = 9, slow: int = 21) -> None:
        self.fast = fast
        self.slow = slow

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        values = [c.close for c in closes]
        if len(values) < self.slow + 1:
            return StrategySignal(
                SignalSide.HOLD,
                last.open_time,
                None,
                None,
                "warmup",
            )
        fast_s = _ema(values, self.fast)
        slow_s = _ema(values, self.slow)
        i = len(values) - 1
        f0, s0 = fast_s[i - 1], slow_s[i - 1]
        f1, s1 = fast_s[i], slow_s[i]
        if None in (f0, s0, f1, s1):
            return StrategySignal(SignalSide.HOLD, last.open_time, f1, s1, "warmup")
        assert f0 is not None and s0 is not None and f1 is not None and s1 is not None
        # Cross from at/below to above → BUY; from at/above to below → SELL
        if f0 <= s0 and f1 > s1:
            side = SignalSide.BUY
        elif f0 >= s0 and f1 < s1:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, f1, s1, None)
