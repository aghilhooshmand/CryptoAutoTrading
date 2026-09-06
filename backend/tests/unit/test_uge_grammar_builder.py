"""Unit: grammar builder (Feature 020b)."""

from __future__ import annotations

import pytest

from app.uge_search.errors import UgeSearchError
from app.uge_search.grammar_builder import build_grammar, build_grammar_from_bnf
from app.uge_search.runner import run_uge_search
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_build_grammar_restricts_ops():
    g = build_grammar(leaves=["dual_ema", "rsi"], composition_ops=["and"])
    assert "macd" not in g.bnf_text.split("<leaf>")[1].split("\n")[0] or "macd(" not in g.bnf_text
    assert "or(" not in g.bnf_text
    assert "and(" in g.bnf_text


def test_empty_leaves_rejected():
    with pytest.raises(UgeSearchError):
        build_grammar(leaves=[], composition_ops=["and"])


def test_build_grammar_from_bnf_roundtrip():
    built = build_grammar(leaves=["rsi"], composition_ops=[])
    again = build_grammar_from_bnf(built.bnf_text)
    assert "<rsi_period>" in again.bnf_text
    assert again.grammar is not None


def test_build_grammar_from_bnf_rejects_empty():
    with pytest.raises(UgeSearchError):
        build_grammar_from_bnf("   ")


def test_custom_param_alts_appear_in_bnf():
    g = build_grammar(
        leaves=["rsi"],
        composition_ops=[],
        param_alternatives={"rsi.period": [11, 22]},
    )
    assert "11 | 22" in g.bnf_text


def test_structured_run_avoids_disallowed_leaf():
    candles = build_fixture_candles(80)
    built = build_grammar(leaves=["rsi"], composition_ops=[])
    r = run_uge_search(
        candles,
        seed=5,
        population_size=6,
        n_generations=2,
        grammar=built.grammar,
        grammar_id=built.grammar_id,
    )
    assert r.best_phenotype is None or (
        "macd" not in (r.best_phenotype or "") and "dual_ema" not in (r.best_phenotype or "")
    )
    if r.best_phenotype:
        assert r.best_phenotype.startswith("rsi(")
