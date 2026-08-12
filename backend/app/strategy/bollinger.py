"""Bollinger Bands recovery-crossover — canonical id ``bollinger_bands``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.indicators import population_stdev_series, sma_series
from app.strategy.params import ParamDef
from app.strategy.registry import StrategyConstraint, StrategyRegistration, register

BOLLINGER_PARAMS = [
    ParamDef(name="period", type="integer", label="Period", default=20, minimum=2),
    ParamDef(
        name="stdDev",
        type="decimal_string",
        label="Std deviations",
        default="2.0",
        minimum=0,
        exclusive_minimum=True,
    ),
]


class BollingerBandsStrategy:
    def __init__(self, period: int = 20, std_dev: str = "2.0") -> None:
        self.period = period
        self.std_dev = Decimal(std_dev)

    def min_history_candles(self) -> int:
        return self.period

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        values = [c.close for c in closes]
        if len(values) < self.period + 1:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")

        mid = sma_series(values, self.period)
        stdev = population_stdev_series(values, self.period)
        i = len(values) - 1
        m1, s1 = mid[i], stdev[i]
        m0, s0 = mid[i - 1], stdev[i - 1]
        if None in (m0, m1, s0, s1):
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")

        lower0 = m0 - self.std_dev * s0
        upper0 = m0 + self.std_dev * s0
        lower1 = m1 - self.std_dev * s1
        upper1 = m1 + self.std_dev * s1
        c0, c1 = values[i - 1], values[i]

        # FR-006 recovery crossover: from strictly below lower to at/above;
        # from strictly above upper to at/below. With population σ and k=2,
        # period must be > 5 for a window member to sit strictly outside
        # mean±2σ (bound is sqrt(n-1)); defaults use period 20.
        if c0 < lower0 and c1 >= lower1:
            side = SignalSide.BUY
        elif c0 > upper0 and c1 <= upper1:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, lower1, upper1, None)


def _factory(params: dict[str, Any]) -> BollingerBandsStrategy:
    return BollingerBandsStrategy(
        period=int(params["period"]),
        std_dev=str(params["stdDev"]),
    )


def register_bollinger_bands() -> None:
    register(
        StrategyRegistration(
            strategy_id="bollinger_bands",
            display_name="Bollinger Bands",
            aliases=[],
            parameters=list(BOLLINGER_PARAMS),
            constraints=[
                StrategyConstraint(
                    code="std_dev_gt_zero",
                    message="Std deviations must be greater than 0.",
                    fields=["stdDev"],
                )
            ],
            factory=_factory,
        )
    )


register_bollinger_bands()
