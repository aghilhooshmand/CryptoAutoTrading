"""RSI recovery-crossover strategy — canonical id ``rsi``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal
from app.strategy.indicators import wilder_rsi_series
from app.strategy.params import ParamDef, StrategyParamError
from app.strategy.registry import StrategyConstraint, StrategyRegistration, register

OVERSOLD_LT_OVERBOUGHT = "Oversold threshold must be less than overbought threshold."

RSI_PARAMS = [
    ParamDef(name="period", type="integer", label="RSI period", default=14, minimum=2),
    ParamDef(name="overbought", type="integer", label="Overbought", default=70, minimum=1, maximum=99),
    ParamDef(name="oversold", type="integer", label="Oversold", default=30, minimum=1, maximum=99),
]


def _validate_oversold_lt_overbought(params: dict[str, Any]) -> None:
    if int(params["oversold"]) >= int(params["overbought"]):
        raise StrategyParamError("invalid_strategy_params", OVERSOLD_LT_OVERBOUGHT)


class RsiStrategy:
    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30) -> None:
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def min_history_candles(self) -> int:
        return self.period

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        values = [c.close for c in closes]
        if len(values) < self.period + 1:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        rsi = wilder_rsi_series(values, self.period)
        i = len(values) - 1
        r0, r1 = rsi[i - 1], rsi[i]
        if r0 is None or r1 is None:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        os_dec = Decimal(self.oversold)
        ob_dec = Decimal(self.overbought)
        if r0 < os_dec and r1 >= os_dec:
            side = SignalSide.BUY
        elif r0 > ob_dec and r1 <= ob_dec:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, r1, None, None)


def _factory(params: dict[str, Any]) -> RsiStrategy:
    return RsiStrategy(
        period=int(params["period"]),
        overbought=int(params["overbought"]),
        oversold=int(params["oversold"]),
    )


def register_rsi() -> None:
    register(
        StrategyRegistration(
            strategy_id="rsi",
            display_name="RSI",
            aliases=[],
            parameters=list(RSI_PARAMS),
            constraints=[
                StrategyConstraint(
                    code="oversold_lt_overbought",
                    message=OVERSOLD_LT_OVERBOUGHT,
                    fields=["oversold", "overbought"],
                )
            ],
            factory=_factory,
            validate_extra=_validate_oversold_lt_overbought,
        )
    )


register_rsi()
