"""History immunity: Settings changes must not rewrite effective configs."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.market_data.models import MarketQuote, MarketStatus
from app.settings.starters import product_starter_defaults


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/s.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    candles = [
        MagicMock(
            open_time=1_700_000_000_000 + i * 3_600_000,
            open="100",
            high="101",
            low="99",
            close="100.5",
            volume="1",
            close_time=1_700_000_000_000 + i * 3_600_000 + 3_599_999,
        )
        for i in range(80)
    ]
    mock_bt = MagicMock()
    mock_bt.get_candles.return_value = candles
    monkeypatch.setattr("app.backtest.service.get_market_data_service", lambda: mock_bt)
    monkeypatch.setattr("app.comparison.service.get_market_data_service", lambda: mock_bt)

    async def _quote(symbol: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000.00",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    mock_sim = AsyncMock()
    mock_sim.get_quote = AsyncMock(side_effect=_quote)

    with patch("app.simulation.session_service.get_market_data_service", return_value=mock_sim):
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock_sim):
            with patch("app.simulation.worker.ensure_worker_running"):
                with TestClient(app) as c:
                    c.put("/portfolio/funding", json={"cash": "100000"})
                    yield c


def _mutate_settings(client) -> None:
    settings = product_starter_defaults()
    settings.update(
        {
            "feeRate": "0.009",
            "startingCapital": "9999",
            "allocatedCapital": "9999",
            "maxPositionSize": "1000",
        }
    )
    assert client.put("/settings", json=settings).status_code == 200


def test_settings_change_does_not_rewrite_backtest(client):
    create = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_000_000 + 79 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "feeRate": "0.002",
        "slippageRate": "0.0005",
        "strategyId": "dual_ema",
        "strategyParams": {"fastPeriod": 9, "slowPeriod": 21},
    }
    r = client.post("/backtest/runs", json=create)
    assert r.status_code == 201, r.text
    run = r.json()
    run_id = run["id"]
    original_fee = run["feeRate"]
    original_starting = run["startingCapital"]

    _mutate_settings(client)

    again = client.get(f"/backtest/runs/{run_id}")
    assert again.status_code == 200
    data = again.json()
    assert data["feeRate"] == original_fee
    assert data["startingCapital"] == original_starting


def test_settings_change_does_not_rewrite_simulation(client):
    body = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startingCapital": "500",
        "allocatedCapital": "500",
        "maxPositionSize": "500",
        "targetNetProfitRate": "0.01",
        "maxSessionLossRate": "0.007",
        "maxTrades": 20,
        "durationSeconds": 3600,
        "feeRate": "0.002",
        "slippageRate": "0.0005",
        "strategyId": "dual_ema",
        "strategyParams": {"fastPeriod": 9, "slowPeriod": 21},
    }
    r = client.post("/simulation/sessions", json=body)
    assert r.status_code == 201, r.text
    session = r.json()
    sid = session["id"]
    original_fee = session["feeRate"]
    original_starting = session["startingCapital"]

    _mutate_settings(client)

    again = client.get(f"/simulation/sessions/{sid}")
    assert again.status_code == 200
    data = again.json()
    assert data["feeRate"] == original_fee
    assert data["startingCapital"] == original_starting


def test_settings_change_does_not_rewrite_comparison(client):
    create = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_000_000 + 79 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "feeRate": "0.002",
        "slippageRate": "0.0005",
        "legs": [
            {"strategyId": "dual_ema", "strategyParams": {"fastPeriod": 9, "slowPeriod": 21}},
            {"strategyId": "rsi", "strategyParams": {"period": 14, "overbought": 70, "oversold": 30}},
        ],
    }
    r = client.post("/comparisons", json=create)
    assert r.status_code == 201, r.text
    comparison = r.json()
    cid = comparison["id"]
    original_fee = comparison["feeRate"]
    original_starting = comparison["startingCapital"]

    _mutate_settings(client)

    again = client.get(f"/comparisons/{cid}")
    assert again.status_code == 200
    data = again.json()
    assert data["feeRate"] == original_fee
    assert data["startingCapital"] == original_starting
