"""Freeze → registry → backtest bind path (Feature 020c)."""

from __future__ import annotations

from pathlib import Path

from app.strategy.registry import build_from_stored, is_known_strategy_id
from app.uge_search import experiment_store as store
from app.uge_search.frozen_catalogue import freeze_best_phenotype
from app.torque_bind.bind import ensure_strategies_registered


def test_frozen_strategy_builds(tmp_path: Path, monkeypatch):
    ensure_strategies_registered()
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path / "exp",
    )
    meta = store.create_experiment_meta(
        config={"seed": 1},
        status="completed",
        base=tmp_path / "exp",
    )
    store.update_meta(
        meta["id"],
        {
            "status": "completed",
            "bestPhenotype": "dual_ema(fastPeriod=9, slowPeriod=21)",
        },
        base=tmp_path / "exp",
    )
    entry = freeze_best_phenotype(
        meta["id"],
        "Catalogue BT",
        base=tmp_path / "frozen",
        experiments_base=tmp_path / "exp",
    )
    assert is_known_strategy_id(entry["strategyId"])
    strategy = build_from_stored(entry["strategyId"], {})
    assert strategy.min_history_candles() >= 21
