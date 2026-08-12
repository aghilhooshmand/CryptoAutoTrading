"""Breakout every-new-extreme — canonical id ``breakout``."""

from __future__ import annotations

from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.params import ParamDef
from app.strategy.registry import StrategyRegistration, register

BREAKOUT_PARAMS = [
    ParamDef(name="lookback", type="integer", label="Lookback", default=20, minimum=2),
]


class BreakoutStrategy:
    def __init__(self, lookback: int = 20) -> None:
        self.lookback = lookback

    def min_history_candles(self) -> int:
        return self.lookback

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        values = [c.close for c in closes]
        if len(values) < self.lookback + 1:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")

        window = values[-(self.lookback + 1) : -1]
        prior_high = max(window)
        prior_low = min(window)
        current = values[-1]

        if current > prior_high:
            side = SignalSide.BUY
        elif current < prior_low:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, prior_high, prior_low, None)


def _factory(params: dict[str, Any]) -> BreakoutStrategy:
    return BreakoutStrategy(lookback=int(params["lookback"]))


def register_breakout() -> None:
    register(
        StrategyRegistration(
            strategy_id="breakout",
            display_name="Breakout",
            aliases=[],
            parameters=list(BREAKOUT_PARAMS),
            constraints=[],
            factory=_factory,
        )
    )


register_breakout()
