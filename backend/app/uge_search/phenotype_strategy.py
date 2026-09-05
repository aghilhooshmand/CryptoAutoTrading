"""Backtest-selectable Torque phenotype strategy (Feature 019 US3)."""

from __future__ import annotations

from typing import Any, Sequence

from app.strategy.base import CandleClose, Strategy, StrategySignal
from app.strategy.params import ParamDef, StrategyParamError
from app.strategy.registry import StrategyRegistration, register
from app.torque_bind.bind import bind_phenotype, ensure_strategies_registered
from app.torque_bind.errors import TorqueBindError

PHENOTYPE_STRATEGY_ID = "torque_phenotype"

TORQUE_PHENOTYPE_PARAMS = [
    ParamDef(
        name="phenotype",
        type="string",
        label="Torque phenotype",
        default="rsi(period=14, oversold=30, overbought=70)",
        required=True,
    ),
]


class TorquePhenotypeStrategy:
    """Delegates to Feature 016-bound Strategy from a phenotype string."""

    def __init__(self, phenotype: str, inner: Strategy) -> None:
        self.phenotype = phenotype
        self._inner = inner

    def min_history_candles(self) -> int:
        return self._inner.min_history_candles()

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        return self._inner.evaluate(closes)


def _factory(params: dict[str, Any]) -> TorquePhenotypeStrategy:
    ensure_strategies_registered()
    phenotype = str(params.get("phenotype", "")).strip()
    if not phenotype:
        raise StrategyParamError("invalid_strategy_params", "phenotype is required")
    try:
        inner = bind_phenotype(phenotype)
    except TorqueBindError as exc:
        raise StrategyParamError("invalid_strategy_params", exc.message) from exc
    return TorquePhenotypeStrategy(phenotype, inner)


def register_torque_phenotype() -> None:
    register(
        StrategyRegistration(
            strategy_id=PHENOTYPE_STRATEGY_ID,
            display_name="Torque phenotype (UGE / frozen)",
            aliases=[],
            parameters=list(TORQUE_PHENOTYPE_PARAMS),
            constraints=[],
            factory=_factory,
        )
    )


register_torque_phenotype()
