"""Persist / load frozen UGE artifacts (Feature 019 US3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.uge_search.errors import UgeSearchError
from app.uge_search.persist import (
    list_frozen_artifacts,
    load_frozen_phenotype,
    persist_run_result,
)
from app.uge_search.runner import UgeRunResult


def test_persist_and_load(tmp_path: Path):
    result = UgeRunResult(
        status="completed",
        termination_reason="done",
        best_phenotype="rsi(period=14, oversold=30, overbought=70)",
        train_fitness=1.5,
        validation_fitness=0.5,
        test_fitness=None,
        fitness_id="net_minus_bh",
        seed=7,
        grammar_id="trading_mvp",
        split={"trainRatio": 0.6, "valRatio": 0.2, "testRatio": 0.2},
        population_size=8,
        n_generations=3,
    )
    path = persist_run_result(result, directory=tmp_path, artifact_id="11111111-1111-1111-1111-111111111111")
    assert path.is_file()
    assert load_frozen_phenotype(path) == result.best_phenotype
    listed = list_frozen_artifacts(tmp_path)
    assert len(listed) == 1
    assert listed[0]["phenotype"] == result.best_phenotype


def test_persist_requires_phenotype(tmp_path: Path):
    result = UgeRunResult(
        status="failed",
        termination_reason="none",
        best_phenotype=None,
        train_fitness=None,
        validation_fitness=None,
        test_fitness=None,
        fitness_id="net_minus_bh",
        seed=1,
        grammar_id="trading_mvp",
        split={},
        population_size=2,
        n_generations=1,
    )
    with pytest.raises(UgeSearchError):
        persist_run_result(result, directory=tmp_path)
