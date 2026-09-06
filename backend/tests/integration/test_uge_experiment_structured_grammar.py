"""Structured leaves/ops constrain phenotypes (Feature 020 convergence T044)."""

from __future__ import annotations

from app.uge_search.grammar_builder import build_grammar
from app.uge_search.runner import run_uge_search
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_restricted_leaves_and_ops_in_best_phenotype():
    candles = build_fixture_candles(80)
    built = build_grammar(
        leaves=["dual_ema", "rsi"],
        composition_ops=["and"],
        param_alternatives={
            "rsi.period": [14],
            "dual_ema.fastPeriod": [9],
            "dual_ema.slowPeriod": [21],
        },
    )
    assert "macd(" not in built.bnf_text
    assert "or(" not in built.bnf_text
    assert "vote(" not in built.bnf_text
    assert "and(" in built.bnf_text

    phenotypes: list[str] = []

    def on_gen(snap: dict) -> None:
        ph = snap.get("bestPhenotype")
        if ph:
            phenotypes.append(str(ph))

    result = run_uge_search(
        candles,
        seed=19,
        population_size=8,
        n_generations=3,
        grammar=built.grammar,
        grammar_id=built.grammar_id,
        on_generation=on_gen,
    )
    samples = list(phenotypes)
    if result.best_phenotype:
        samples.append(result.best_phenotype)
    assert samples, "expected at least one mapped phenotype"
    for ph in samples:
        assert "macd(" not in ph
        assert "or(" not in ph
        assert "vote(" not in ph
        assert "rsi(" in ph or "dual_ema(" in ph or ph.startswith("and(")
