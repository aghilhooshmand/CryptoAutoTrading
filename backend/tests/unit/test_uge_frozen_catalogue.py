"""Frozen catalogue freeze rules (Feature 020c)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.strategy.registry import is_known_strategy_id
from app.uge_search import experiment_store as store
from app.uge_search.errors import DUPLICATE_DISPLAY_NAME, EXPERIMENT_NOT_TERMINAL, UgeSearchError
from app.uge_search.frozen_catalogue import freeze_best_phenotype


def test_freeze_requires_terminal_and_unique_name(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(store, "DEFAULT_EXPERIMENTS_DIR", tmp_path / "exp")
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path / "exp",
    )
    frozen = tmp_path / "frozen"
    meta = store.create_experiment_meta(config={"seed": 1}, status="running", base=tmp_path / "exp")
    eid = meta["id"]
    with pytest.raises(UgeSearchError) as ei:
        freeze_best_phenotype(eid, "A", base=frozen, experiments_base=tmp_path / "exp")
    assert ei.value.code == EXPERIMENT_NOT_TERMINAL

    store.update_meta(
        eid,
        {"status": "completed", "bestPhenotype": "rsi(period=14, oversold=30, overbought=70)"},
        base=tmp_path / "exp",
    )
    entry = freeze_best_phenotype(eid, "My UGE Strat", base=frozen, experiments_base=tmp_path / "exp")
    assert is_known_strategy_id(entry["strategyId"])
    with pytest.raises(UgeSearchError) as e2:
        freeze_best_phenotype(eid, "My UGE Strat", base=frozen, experiments_base=tmp_path / "exp")
    assert e2.value.code == DUPLICATE_DISPLAY_NAME
