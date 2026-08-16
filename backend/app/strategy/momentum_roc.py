"""Rate-of-change / momentum — canonical id ``roc_momentum``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.params import ParamDef
from app.strategy.registry import StrategyRegistration, register
from app.simulation.money import quantize_money

ROC_PARAMS = [
    ParamDef(name="period", type="integer", label="ROC period", default=12, minimum=1),
    ParamDef(
        name="buyThreshold",
        type="decimal_string",
        label="Buy when ROC crosses above",
        default="0",
    ),
    ParamDef(
        name="sellThreshold",
        type="decimal_string",
        label="Sell when ROC crosses below",
        default="0",
    ),
]


class RocMomentumStrategy:
    def __init__(
        self,
        period: int = 12,
        buy_threshold: str = "0",
        sell_threshold: str = "0",
    ) -> None:
        self.period = period
        self.buy_threshold = Decimal(buy_threshold)
        self.sell_threshold = Decimal(sell_threshold)

    def min_history_candles(self) -> int:
        return self.period + 1

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        vals = [c.close for c in closes]
        if len(vals) < self.period + 2:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        i = len(vals) - 1
        prev = vals[i - self.period]
        prev2 = vals[i - 1 - self.period]
        if prev == 0 or prev2 == 0:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        roc1 = quantize_money((vals[i] - prev) / prev * Decimal("100"))
        roc0 = quantize_money((vals[i - 1] - prev2) / prev2 * Decimal("100"))
        if roc0 < self.buy_threshold and roc1 >= self.buy_threshold:
            side = SignalSide.BUY
        elif roc0 > self.sell_threshold and roc1 <= self.sell_threshold:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, roc1, None, None)


def _factory(params: dict[str, Any]) -> RocMomentumStrategy:
    return RocMomentumStrategy(
        period=int(params["period"]),
        buy_threshold=str(params["buyThreshold"]),
        sell_threshold=str(params["sellThreshold"]),
    )


def register_roc_momentum() -> None:
    register(
        StrategyRegistration(
            strategy_id="roc_momentum",
            display_name="ROC Momentum",
            aliases=[],
            parameters=list(ROC_PARAMS),
            constraints=[],
            factory=_factory,
        )
    )


register_roc_momentum()
