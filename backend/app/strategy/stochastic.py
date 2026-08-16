"""Stochastic oscillator recovery-crossover — canonical id ``stochastic``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal, bar_high, bar_low
from app.strategy.indicators import stochastic_k_series
from app.strategy.params import ParamDef, StrategyParamError
from app.strategy.registry import StrategyConstraint, StrategyRegistration, register

OVERSOLD_LT_OVERBOUGHT = "Oversold threshold must be less than overbought threshold."

STOCHASTIC_PARAMS = [
    ParamDef(name="kPeriod", type="integer", label="%K period", default=14, minimum=2),
    ParamDef(name="dPeriod", type="integer", label="%D period", default=3, minimum=1),
    ParamDef(name="overbought", type="integer", label="Overbought", default=80, minimum=1, maximum=99),
    ParamDef(name="oversold", type="integer", label="Oversold", default=20, minimum=1, maximum=99),
]


def _validate_oversold_lt_overbought(params: dict[str, Any]) -> None:
    if int(params["oversold"]) >= int(params["overbought"]):
        raise StrategyParamError("invalid_strategy_params", OVERSOLD_LT_OVERBOUGHT)


class StochasticStrategy:
    def __init__(
        self,
        k_period: int = 14,
        d_period: int = 3,
        overbought: int = 80,
        oversold: int = 20,
    ) -> None:
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold

    def min_history_candles(self) -> int:
        return self.k_period + self.d_period

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        highs = [bar_high(c) for c in closes]
        lows = [bar_low(c) for c in closes]
        vals = [c.close for c in closes]
        need = self.k_period + self.d_period
        if len(vals) < need:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        k = stochastic_k_series(highs, lows, vals, self.k_period)
        d = _stochastic_d_series(k, self.d_period)
        i = len(vals) - 1
        if k[i] is None or d[i] is None or k[i - 1] is None or d[i - 1] is None:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        k0, k1 = k[i - 1], k[i]
        d0, d1 = d[i - 1], d[i]
        assert k0 is not None and k1 is not None and d0 is not None and d1 is not None
        os_dec = Decimal(self.oversold)
        ob_dec = Decimal(self.overbought)
        # Recovery crossover of %K through thresholds (same spirit as RSI)
        if k0 < os_dec and k1 >= os_dec:
            side = SignalSide.BUY
        elif k0 > ob_dec and k1 <= ob_dec:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, k1, d1, None)


def _stochastic_d_series(
    k: list[Decimal | None], d_period: int
) -> list[Decimal | None]:
    """SMA of %K; requires a full window of defined %K values."""
    from app.simulation.money import quantize_money

    n = len(k)
    out: list[Decimal | None] = [None] * n
    if d_period < 1:
        return out
    for i in range(d_period - 1, n):
        window = k[i - d_period + 1 : i + 1]
        if any(x is None for x in window):
            continue
        out[i] = quantize_money(sum(window, Decimal("0")) / Decimal(d_period))  # type: ignore[arg-type]
    return out


def _factory(params: dict[str, Any]) -> StochasticStrategy:
    return StochasticStrategy(
        k_period=int(params["kPeriod"]),
        d_period=int(params["dPeriod"]),
        overbought=int(params["overbought"]),
        oversold=int(params["oversold"]),
    )


def register_stochastic() -> None:
    register(
        StrategyRegistration(
            strategy_id="stochastic",
            display_name="Stochastic",
            aliases=[],
            parameters=list(STOCHASTIC_PARAMS),
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


register_stochastic()
