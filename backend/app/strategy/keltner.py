"""Keltner Channel recovery-crossover — canonical id ``keltner_channel``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.strategy.base import CandleClose, SignalSide, StrategySignal, bar_high, bar_low
from app.strategy.indicators import atr_series, ema_series
from app.strategy.params import ParamDef
from app.strategy.registry import StrategyRegistration, register

KELTNER_PARAMS = [
    ParamDef(name="emaPeriod", type="integer", label="EMA period", default=20, minimum=2),
    ParamDef(name="atrPeriod", type="integer", label="ATR period", default=10, minimum=1),
    ParamDef(
        name="atrMult",
        type="decimal_string",
        label="ATR multiplier",
        default="1.5",
        minimum=0,
        exclusive_minimum=True,
    ),
]


class KeltnerChannelStrategy:
    def __init__(self, ema_period: int = 20, atr_period: int = 10, atr_mult: str = "1.5") -> None:
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.atr_mult = Decimal(atr_mult)

    def min_history_candles(self) -> int:
        return max(self.ema_period, self.atr_period) + 1

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        if not closes:
            return StrategySignal(SignalSide.HOLD, 0, None, None, "no_candles")
        last = closes[-1]
        vals = [c.close for c in closes]
        highs = [bar_high(c) for c in closes]
        lows = [bar_low(c) for c in closes]
        need = max(self.ema_period, self.atr_period) + 1
        if len(vals) < need:
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        mid = ema_series(vals, self.ema_period)
        atr = atr_series(highs, lows, vals, self.atr_period)
        i = len(vals) - 1
        m0, m1 = mid[i - 1], mid[i]
        a0, a1 = atr[i - 1], atr[i]
        if None in (m0, m1, a0, a1):
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "warmup")
        assert m0 is not None and m1 is not None and a0 is not None and a1 is not None
        lower0 = m0 - self.atr_mult * a0
        upper0 = m0 + self.atr_mult * a0
        lower1 = m1 - self.atr_mult * a1
        upper1 = m1 + self.atr_mult * a1
        c0, c1 = vals[i - 1], vals[i]
        # Recovery crossover like Bollinger: from below lower to at/above; from above upper to at/below
        if c0 < lower0 and c1 >= lower1:
            side = SignalSide.BUY
        elif c0 > upper0 and c1 <= upper1:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD
        return StrategySignal(side, last.open_time, lower1, upper1, None)


def _factory(params: dict[str, Any]) -> KeltnerChannelStrategy:
    return KeltnerChannelStrategy(
        ema_period=int(params["emaPeriod"]),
        atr_period=int(params["atrPeriod"]),
        atr_mult=str(params["atrMult"]),
    )


def register_keltner_channel() -> None:
    register(
        StrategyRegistration(
            strategy_id="keltner_channel",
            display_name="Keltner Channel",
            aliases=[],
            parameters=list(KELTNER_PARAMS),
            constraints=[],
            factory=_factory,
        )
    )


register_keltner_channel()
