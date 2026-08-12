"""MACD line/signal crossover — canonical id ``macd``."""

from __future__ import annotations

from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.indicators import ema_series
from app.strategy.params import ParamDef, StrategyParamError
from app.strategy.registry import StrategyConstraint, StrategyRegistration, register

FAST_LT_SLOW_MESSAGE = "Fast period must be less than slow period."

MACD_PARAMS = [
    ParamDef(name="fastPeriod", type="integer", label="Fast period", default=12, minimum=1),
    ParamDef(name="slowPeriod", type="integer", label="Slow period", default=26, minimum=2),
    ParamDef(name="signalPeriod", type="integer", label="Signal period", default=9, minimum=1),
]


def _validate_fast_lt_slow(params: dict[str, Any]) -> None:
    if int(params["fastPeriod"]) >= int(params["slowPeriod"]):
        raise StrategyParamError("invalid_strategy_params", FAST_LT_SLOW_MESSAGE)


class MacdStrategy:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def min_history_candles(self) -> int:
        return self.slow + self.signal

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        values = [c.close for c in closes]
        if len(values) < self.min_history_candles() + 1:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")

        fast_ema = ema_series(values, self.fast)
        slow_ema = ema_series(values, self.slow)
        macd_line: list = [None] * len(values)
        for i in range(len(values)):
            f, s = fast_ema[i], slow_ema[i]
            if f is not None and s is not None:
                macd_line[i] = f - s

        macd_indices = [i for i, m in enumerate(macd_line) if m is not None]
        macd_dense = [macd_line[i] for i in macd_indices]
        if len(macd_dense) < self.signal + 1:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")

        signal_dense = ema_series(macd_dense, self.signal)
        signal_line: list = [None] * len(values)
        for k, sig in enumerate(signal_dense):
            if sig is not None:
                signal_line[macd_indices[k]] = sig

        i = len(values) - 1
        m0, m1 = macd_line[i - 1], macd_line[i]
        s0, s1 = signal_line[i - 1], signal_line[i]
        if None in (m0, m1, s0, s1):
            return StrategySignal(SignalSide.HOLD, last.open_time, m1, s1, "warmup")
        if m0 <= s0 and m1 > s1:
            side = SignalSide.BUY
        elif m0 >= s0 and m1 < s1:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, m1, s1, None)


def _factory(params: dict[str, Any]) -> MacdStrategy:
    return MacdStrategy(
        fast=int(params["fastPeriod"]),
        slow=int(params["slowPeriod"]),
        signal=int(params["signalPeriod"]),
    )


def register_macd() -> None:
    register(
        StrategyRegistration(
            strategy_id="macd",
            display_name="MACD",
            aliases=[],
            parameters=list(MACD_PARAMS),
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


register_macd()
