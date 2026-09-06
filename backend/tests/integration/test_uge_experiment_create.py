"""Create-path reject tests (Feature 020 convergence T043)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.uge_search.errors import INVALID_EXPERIMENT_CONFIG, UgeSearchError
from app.uge_search.experiment_runner import reset_experiment_runner_for_tests
from app.uge_search.experiment_service import start_experiment_with_candles, validate_create_body
from tests.integration.test_uge_offline_run import build_fixture_candles


def test_validate_rejects_bad_split_ratios():
    with pytest.raises(UgeSearchError) as ei:
        validate_create_body(
            {
                "symbol": "btc_usdt",
                "timeframe": "1h",
                "startTime": "2024-01-01T00:00:00Z",
                "endTime": "2024-02-01T00:00:00Z",
                "trainRatio": 0.9,
                "valRatio": 0.9,
                "testRatio": 0.9,
            }
        )
    assert ei.value.code == INVALID_EXPERIMENT_CONFIG


def test_start_rejects_short_candle_window(tmp_path: Path, monkeypatch):
    reset_experiment_runner_for_tests()
    monkeypatch.setattr(
        "app.uge_search.experiment_store.DEFAULT_EXPERIMENTS_DIR",
        tmp_path,
    )
    candles = build_fixture_candles(10)
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
    with pytest.raises(UgeSearchError) as ei:
        start_experiment_with_candles(config, candles)
    assert ei.value.code == INVALID_EXPERIMENT_CONFIG
    assert "candles" in ei.value.message.lower()
