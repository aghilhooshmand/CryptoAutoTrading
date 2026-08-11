"""Dual EMA crossover — canonical id `dual_ema`, defaults fast=9 slow=21."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.simulation.money import quantize_money
from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.params import ParamDef, StrategyParamError
from app.strategy.registry import (
    StrategyConstraint,
    StrategyRegistration,
    register,
)


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


FAST_LT_SLOW_MESSAGE = "Fast period must be less than slow period."

DUAL_EMA_PARAMS = [
    ParamDef(
        name="fastPeriod",
        type="integer",
        label="Fast EMA period",
        default=9,
        minimum=1,
    ),
    ParamDef(
        name="slowPeriod",
        type="integer",
        label="Slow EMA period",
        default=21,
        minimum=2,
    ),
]


def _validate_fast_lt_slow(params: dict[str, Any]) -> None:
    fast = int(params["fastPeriod"])
    slow = int(params["slowPeriod"])
    if fast >= slow:
        raise StrategyParamError("invalid_strategy_params", FAST_LT_SLOW_MESSAGE)


class DualEmaCrossoverStrategy:
    def __init__(self, fast: int = 9, slow: int = 21) -> None:
        self.fast = fast
        self.slow = slow

    def min_history_candles(self) -> int:
        return self.slow

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
        if f0 <= s0 and f1 > s1:
            side = SignalSide.BUY
        elif f0 >= s0 and f1 < s1:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, f1, s1, None)


def _factory(params: dict[str, Any]) -> DualEmaCrossoverStrategy:
    return DualEmaCrossoverStrategy(
        fast=int(params["fastPeriod"]),
        slow=int(params["slowPeriod"]),
    )


def register_dual_ema() -> None:
    register(
        StrategyRegistration(
            strategy_id="dual_ema",
            display_name="Dual EMA",
            aliases=["dual_ema_9_21"],
            parameters=list(DUAL_EMA_PARAMS),
            constraints=[
                StrategyConstraint(
                    code="fast_lt_slow",
                    message=FAST_LT_SLOW_MESSAGE,
                    fields=["fastPeriod", "slowPeriod"],
                )
            ],
            factory=_factory,
            validate_extra=_validate_fast_lt_slow,
        )
    )


# Auto-register on import
register_dual_ema()
