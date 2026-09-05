"""Offline UGE run integration (Feature 019 US1/US2)."""

from __future__ import annotations

from app.market_data.models import Candlestick
from app.torque_bind.bind import ensure_strategies_registered
from app.torque_bind import evaluate_phenotype
from app.uge_search.fitness import scalar_from_metrics
from app.uge_search.grammar_mvp import trading_mvp_bnf_text
from app.uge_search.runner import run_uge_search
from app.uge_search.splits import chronological_split


def build_fixture_candles(n: int = 80) -> list[Candlestick]:
    out: list[Candlestick] = []
    start = 1_700_000_000_000
    step = 3_600_000
    px_cents = 12000
    for i in range(n):
        if i < 35:
            px_cents -= 80
        else:
            px_cents += 100
        px = f"{px_cents / 100:.2f}"
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=px,
                high=f"{(px_cents + 50) / 100:.2f}",
                low=f"{(px_cents - 50) / 100:.2f}",
                close=px,
            )
        )
    return out


def test_grammar_lists_leaves_and_compose():
    text = trading_mvp_bnf_text()
    assert "rsi(" in text and "macd(" in text and "dual_ema(" in text
    assert "and(" in text and "or(" in text and "vote(" in text


def test_run_uge_search_seed_replay_and_train_fitness_match():
    ensure_strategies_registered()
    candles = build_fixture_candles()
    a = run_uge_search(
        candles,
        seed=7,
        population_size=6,
        n_generations=2,
        max_depth=5,
        fitness_id="net_minus_bh",
    )
    b = run_uge_search(
        candles,
        seed=7,
        population_size=6,
        n_generations=2,
        max_depth=5,
        fitness_id="net_minus_bh",
    )
    assert a.status in ("completed", "terminated")
    assert a.best_phenotype == b.best_phenotype
    assert a.train_fitness == b.train_fitness
    assert a.best_phenotype
    split = chronological_split(candles)
    out = evaluate_phenotype(
        a.best_phenotype,
        candles=split.train,
        starting_capital="1000",
    )
    assert out["ok"] is True
    expected = scalar_from_metrics("net_minus_bh", out["metrics"])
    assert a.train_fitness is not None
    assert abs(a.train_fitness - expected) < 1e-6
    # Validation may be None if evaluate fails on short val window; when present it's report-only
    assert a.validation_fitness is None or isinstance(a.validation_fitness, float)
    assert a.test_fitness is None  # not scored during search


def test_invalid_phenotype_does_not_abort_population_eval():
    ensure_strategies_registered()
    from types import SimpleNamespace

    from app.uge_search.fitness import make_backtest_evaluator

    candles = build_fixture_candles(40)
    split = chronological_split(candles)
    evaluate = make_backtest_evaluator(split.train)
    # Mixed batch: invalid then valid — evaluator never raises
    inds = [
        SimpleNamespace(mapping=SimpleNamespace(invalid=False, phenotype="!!!")),
        SimpleNamespace(
            mapping=SimpleNamespace(
                invalid=False,
                phenotype="rsi(period=14, oversold=30, overbought=70)",
            )
        ),
    ]
    results = [evaluate(i) for i in inds]
    assert results[0].ok is False
    assert results[1].ok is True
