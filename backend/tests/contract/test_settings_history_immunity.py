"""History immunity: Settings changes must not rewrite effective configs."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.settings.starters import product_starter_defaults


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/s.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    # Avoid live market fetch for backtest create.
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
    mock_svc = MagicMock()
    mock_svc.get_candles.return_value = candles
    monkeypatch.setattr("app.backtest.service.get_market_data_service", lambda: mock_svc)

    with TestClient(app) as c:
        yield c


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

    again = client.get(f"/backtest/runs/{run_id}")
    assert again.status_code == 200
    data = again.json()
    assert data["feeRate"] == original_fee
    assert data["startingCapital"] == original_starting
