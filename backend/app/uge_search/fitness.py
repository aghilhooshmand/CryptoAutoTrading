"""Fitness allow-list + UGE evaluator adapter (Feature 019)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from uge import EvaluationResult, Fitness

from app.market_data.models import Candlestick
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, d
from app.torque_bind import evaluate_phenotype
from app.uge_search.errors import UNKNOWN_FITNESS_ID, UgeSearchError

FITNESS_NET_MINUS_BH = "net_minus_bh"
FITNESS_NET_PROFIT = "net_profit"

FITNESS_ALLOW_LIST: frozenset[str] = frozenset(
    {
        FITNESS_NET_MINUS_BH,
        FITNESS_NET_PROFIT,
    }
)

DEFAULT_FITNESS_ID = FITNESS_NET_MINUS_BH


def resolve_fitness_id(fitness_id: str | None) -> str:
    fid = (fitness_id or DEFAULT_FITNESS_ID).strip()
    if fid not in FITNESS_ALLOW_LIST:
        raise UgeSearchError(
            UNKNOWN_FITNESS_ID,
            f"Unknown fitnessId {fid!r}; allowed: {sorted(FITNESS_ALLOW_LIST)}",
        )
    return fid


def scalar_from_metrics(fitness_id: str, metrics: dict[str, Any]) -> float:
    """Map Feature 016 metrics dict to a single maximise objective."""
    fid = resolve_fitness_id(fitness_id)
    net = float(d(str(metrics["netProfit"])))
    if fid == FITNESS_NET_PROFIT:
        return net
    bh = float(d(str(metrics["buyAndHoldNetProfit"])))
    return net - bh


def make_backtest_evaluator(
    train_candles: list[Candlestick],
    *,
    fitness_id: str = DEFAULT_FITNESS_ID,
    starting_capital: Decimal | str = Decimal("1000"),
    fee_rate: Decimal | str = DEFAULT_FEE_RATE,
    slippage_rate: Decimal | str = DEFAULT_SLIPPAGE_RATE,
) -> Callable[..., EvaluationResult]:
    """
    UGE evaluate callable: phenotype → Feature 016 evaluate on **train** candles only.
    """
    fid = resolve_fitness_id(fitness_id)

    def evaluate(individual: Any, context: Any = None) -> EvaluationResult:
        _ = context
        if individual.mapping.invalid:
            return EvaluationResult(ok=False)
        phenotype = individual.mapping.phenotype
        if not phenotype or not str(phenotype).strip():
            return EvaluationResult(ok=False)
        out = evaluate_phenotype(
            str(phenotype).strip(),
            candles=train_candles,
            starting_capital=starting_capital,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
        )
        if not out.get("ok"):
            return EvaluationResult(ok=False)
        try:
            value = scalar_from_metrics(fid, out["metrics"])
        except (KeyError, ValueError, TypeError):
            return EvaluationResult(ok=False)
        return EvaluationResult(
            ok=True,
            fitness=Fitness([value], ["maximise"]),
        )

    return evaluate


def score_phenotype(
    phenotype: str,
    candles: list[Candlestick],
    *,
    fitness_id: str = DEFAULT_FITNESS_ID,
    starting_capital: Decimal | str = Decimal("1000"),
    fee_rate: Decimal | str = DEFAULT_FEE_RATE,
    slippage_rate: Decimal | str = DEFAULT_SLIPPAGE_RATE,
) -> float | None:
    """Standalone score for post-run validation report; None if evaluate failed."""
    fid = resolve_fitness_id(fitness_id)
    out = evaluate_phenotype(
        phenotype,
        candles=candles,
        starting_capital=starting_capital,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )
    if not out.get("ok"):
        return None
    return scalar_from_metrics(fid, out["metrics"])
