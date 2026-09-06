"""Unit tests for experiment store + singleton runner (Feature 020)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.uge_search import experiment_store as store
from app.uge_search.experiment_runner import (
    ExperimentConflictError,
    reset_experiment_runner_for_tests,
)
from app.uge_search.experiment_service import (
    start_experiment_with_candles,
    validate_create_body,
)
from app.uge_search.grammar_builder import build_grammar
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_store_append_and_read(tmp_path: Path):
    meta = store.create_experiment_meta(
        config={"seed": 1},
        base=tmp_path,
    )
    eid = meta["id"]
    store.append_generation(eid, {"generation": 0, "fitnessMax": 1.5}, base=tmp_path)
    store.append_generation(eid, {"generation": 1, "fitnessMax": 2.0}, base=tmp_path)
    gens = store.read_generations(eid, base=tmp_path)
    assert len(gens) == 2
    assert gens[0]["generation"] == 0
    assert store.read_meta(eid, base=tmp_path)["id"] == eid


def test_concurrent_meta_updates_do_not_raise(tmp_path: Path):
    """Shared meta.json.tmp used to race; unique tmp + lock must stay clean."""
    import threading

    meta = store.create_experiment_meta(config={"seed": 1}, base=tmp_path)
    eid = meta["id"]
    errors: list[BaseException] = []

    def bump(i: int) -> None:
        try:
            for _ in range(40):
                store.update_meta(eid, {"generationCount": i}, base=tmp_path)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=bump, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert store.read_meta(eid, base=tmp_path) is not None


def test_singleton_rejects_second_start(tmp_path: Path, monkeypatch):
    runner = reset_experiment_runner_for_tests()
    started = []

    def slow():
        started.append(1)
        time.sleep(0.4)

    runner.start("exp_a", slow)
    with pytest.raises(ExperimentConflictError):
        runner.start("exp_b", slow)
    # wait for first to finish
    deadline = time.time() + 2
    while runner.is_active() and time.time() < deadline:
        time.sleep(0.05)
    assert started == [1]


def test_validate_create_body_rejects_bad_split():
    with pytest.raises(Exception):
        validate_create_body(
            {
                "symbol": "btc_usdt",
                "timeframe": "1h",
                "startTime": "2024-01-01T00:00:00Z",
                "endTime": "2024-02-01T00:00:00Z",
                "trainRatio": 0.5,
                "valRatio": 0.5,
                "testRatio": 0.5,
            }
        )


def test_grammar_builder_rejects_empty_leaves():
    with pytest.raises(Exception):
        build_grammar(leaves=[], composition_ops=["and"])


def test_start_experiment_streams_generations(tmp_path: Path, monkeypatch):
    reset_experiment_runner_for_tests()
    monkeypatch.setattr(store, "DEFAULT_EXPERIMENTS_DIR", tmp_path)
    # Also patch experiments_dir used via module
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path,
    )
    candles = build_fixture_candles(80)
    config = validate_create_body(
        {
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startTime": candles[0].openTime,
            "endTime": candles[-1].openTime + 1,
            "populationSize": 4,
            "nGenerations": 2,
            "seed": 7,
        }
    )
    meta = start_experiment_with_candles(config, candles)
    eid = meta["id"]
    deadline = time.time() + 30
    while time.time() < deadline:
        m = store.read_meta(eid, base=tmp_path)
        gens = store.read_generations(eid, base=tmp_path)
        if m and m.get("status") in ("completed", "failed", "cancelled"):
            assert len(gens) >= 1
            # generations appeared (stream) — for ngen=2 expect 2 when completed
            if m["status"] == "completed":
                assert len(gens) == 2
            return
        if len(gens) >= 1 and m and m.get("status") == "running":
            # SC-001 style: saw a generation before terminal
            pass
        time.sleep(0.05)
    pytest.fail("experiment did not finish")
