"""Extend offline UGE with generation hooks + cancel (Feature 020)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from uge import Grammar, RankingProjection, UGEEngine

from app.market_data.models import Candlestick
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE
from app.torque_bind.bind import ensure_strategies_registered
from app.uge_search.fitness import (
    DEFAULT_FITNESS_ID,
    make_backtest_evaluator,
    resolve_fitness_id,
    score_phenotype,
)
from app.uge_search.grammar_mvp import GRAMMAR_ID, load_trading_mvp_grammar
from app.uge_search.splits import chronological_split

OnGeneration = Callable[[dict[str, Any]], None]
CancelCheck = Callable[[], bool]


class UgeSearchCancelled(Exception):
    """Raised from a reporter when cancel is requested at a generation boundary."""


@dataclass
class UgeRunResult:
    status: str
    termination_reason: str
    best_phenotype: str | None
    train_fitness: float | None
    validation_fitness: float | None
    test_fitness: float | None
    fitness_id: str
    seed: int
    grammar_id: str
    split: dict[str, float]
    population_size: int
    n_generations: int
    raw_outcome: Any = None
    train_candle_count: int | None = None


def _snapshot_from_record(record: Any, population: Any, archive: Any) -> dict[str, Any]:
    from uge.observe import compute_generation_stats
    from uge import RankingProjection as RP

    stats = compute_generation_stats(
        record,
        population,
        archive,
        ranking=RP("primary_index", {"index": 0}),
        objective_index=0,
    )
    return {
        "generation": int(record.generation),
        "fitnessMax": stats.get("fitness_max"),
        "fitnessAvg": stats.get("fitness_avg"),
        "fitnessMin": stats.get("fitness_min"),
        "bestPhenotype": stats.get("best_phenotype"),
        "nInvalid": getattr(record, "n_invalid", None),
        "nFailedEval": getattr(record, "n_failed_eval", None),
    }


def run_uge_search(
    candles: list[Candlestick],
    *,
    seed: int = 7,
    population_size: int = 8,
    n_generations: int = 3,
    max_depth: int = 6,
    fitness_id: str = DEFAULT_FITNESS_ID,
    starting_capital: Decimal | str = Decimal("1000"),
    fee_rate: Decimal | str = DEFAULT_FEE_RATE,
    slippage_rate: Decimal | str = DEFAULT_SLIPPAGE_RATE,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    score_test: bool = False,
    grammar: Grammar | None = None,
    grammar_id: str | None = None,
    on_generation: OnGeneration | None = None,
    cancel_check: CancelCheck | None = None,
) -> UgeRunResult:
    """
    Run offline UGE on a candle snapshot.

    Selection fitness uses **train** candles only. Validation fitness is
    computed after the run for the best phenotype (report only). Test is
    unused unless ``score_test=True``.
    """
    ensure_strategies_registered()
    fid = resolve_fitness_id(fitness_id)
    split = chronological_split(
        candles,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )
    g = grammar if grammar is not None else load_trading_mvp_grammar()
    gid = grammar_id or GRAMMAR_ID
    evaluator = make_backtest_evaluator(
        split.train,
        fitness_id=fid,
        starting_capital=starting_capital,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )
    engine = UGEEngine()
    engine.register("evaluate", evaluator)
    engine.register("select", "tournament", tournsize=3)
    engine.register("init", "sensible", min_init_depth=1, max_init_depth=min(4, max_depth))
    engine.register("mate", "one_point")
    engine.register("mutate", "codon_flip")
    engine.register("mapping", "lazy")

    cancelled = False
    last_best_pheno: str | None = None
    last_best_fit: float | None = None

    def _reporter(record: Any, population: Any, archive: Any = None) -> None:
        nonlocal cancelled, last_best_pheno, last_best_fit
        snap = _snapshot_from_record(record, population, archive)
        if snap.get("bestPhenotype"):
            last_best_pheno = str(snap["bestPhenotype"])
        if snap.get("fitnessMax") is not None:
            try:
                last_best_fit = float(snap["fitnessMax"])
            except (TypeError, ValueError):
                pass
        if on_generation is not None:
            on_generation(snap)
        if cancel_check is not None and cancel_check():
            cancelled = True
            raise UgeSearchCancelled("cancel requested")

    try:
        outcome = engine.run(
            grammar=g,
            pop=population_size,
            ngen=n_generations,
            max_depth=max_depth,
            seed=seed,
            cxpb=0.8,
            mutpb=0.2,
            elite_size=1,
            archive_capacity=5,
            ranking_projection=RankingProjection("primary_index", {"index": 0}),
            reporters=[_reporter],
        )
        status = outcome.status
        termination_reason = outcome.termination_reason
    except UgeSearchCancelled:
        status = "cancelled"
        termination_reason = "operator_cancel"
        outcome = None

    best = None if outcome is None else outcome.best_individual
    phenotype: str | None = None
    train_fit: float | None = None
    if best is not None and not best.mapping.invalid:
        phenotype = best.mapping.phenotype
        if best.fitness is not None and best.fitness.objectives:
            train_fit = float(best.fitness.objectives[0])
        else:
            train_fit = score_phenotype(
                phenotype,
                split.train,
                fitness_id=fid,
                starting_capital=starting_capital,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
    if phenotype is None and last_best_pheno:
        phenotype = last_best_pheno
        train_fit = last_best_fit
    val_fit: float | None = None
    test_fit: float | None = None
    if phenotype:
        val_fit = score_phenotype(
            phenotype,
            split.validation,
            fitness_id=fid,
            starting_capital=starting_capital,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
        )
        if score_test:
            test_fit = score_phenotype(
                phenotype,
                split.test,
                fitness_id=fid,
                starting_capital=starting_capital,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
    return UgeRunResult(
        status=status if not cancelled else "cancelled",
        termination_reason=termination_reason,
        best_phenotype=phenotype,
        train_fitness=train_fit,
        validation_fitness=val_fit,
        test_fitness=test_fit,
        fitness_id=fid,
        seed=seed,
        grammar_id=gid,
        split={
            "trainRatio": train_ratio,
            "valRatio": val_ratio,
            "testRatio": test_ratio,
        },
        population_size=population_size,
        n_generations=n_generations,
        raw_outcome=outcome,
        train_candle_count=len(split.train),
    )
