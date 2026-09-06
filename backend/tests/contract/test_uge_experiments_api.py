"""Contract smoke for /uge/experiments (Feature 020)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.uge_search.experiment_runner import reset_experiment_runner_for_tests
from app.uge_search.experiment_service import start_experiment_with_candles, validate_create_body
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_experiments_list_empty_ok():
    client = TestClient(app)
    r = client.get("/uge/experiments")
    assert r.status_code == 200
    assert "experiments" in r.json()


def test_create_via_service_then_get(tmp_path, monkeypatch):
    reset_experiment_runner_for_tests()
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
            "nGenerations": 1,
            "seed": 1,
        }
    )
    meta = start_experiment_with_candles(config, candles)
    client = TestClient(app)
    # Point GET at same tmp dir
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path,
    )
    r = client.get(f"/uge/experiments/{meta['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == meta["id"]
