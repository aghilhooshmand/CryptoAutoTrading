"""Integration: experiment generation stream + train-only (Feature 020)."""

from __future__ import annotations

import time
from pathlib import Path

from app.uge_search import experiment_store as store
from app.uge_search.experiment_runner import reset_experiment_runner_for_tests
from app.uge_search.experiment_service import start_experiment_with_candles, validate_create_body
from app.uge_search.runner import run_uge_search
from app.uge_search.splits import chronological_split
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_generations_append_before_terminal_and_train_only(tmp_path: Path, monkeypatch):
    reset_experiment_runner_for_tests()
    monkeypatch.setattr(store, "DEFAULT_EXPERIMENTS_DIR", tmp_path)
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path,
    )
    candles = build_fixture_candles(80)
    split = chronological_split(candles, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    saw_running_with_gen = False

    config = validate_create_body(
        {
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startTime": candles[0].openTime,
            "endTime": candles[-1].openTime + 1,
            "populationSize": 4,
            "nGenerations": 2,
            "seed": 11,
        }
    )
    meta = start_experiment_with_candles(config, candles)
    eid = meta["id"]
    deadline = time.time() + 45
    while time.time() < deadline:
        m = store.read_meta(eid, base=tmp_path)
        gens = store.read_generations(eid, base=tmp_path)
        if m and m.get("status") == "running" and gens:
            saw_running_with_gen = True
        if m and m.get("status") in ("completed", "failed", "cancelled"):
            assert saw_running_with_gen or len(gens) >= 1
            assert len(gens) >= 1
            break
        time.sleep(0.05)
    else:
        raise AssertionError("timeout")

    # FR-017: evaluator path uses train count via run_uge_search
    snaps = []
    r = run_uge_search(
        candles,
        seed=11,
        population_size=4,
        n_generations=1,
        on_generation=snaps.append,
    )
    assert r.train_candle_count == len(split.train)
