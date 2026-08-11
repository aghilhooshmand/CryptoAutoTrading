"""Integration: fixture candles through full backtest pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.market_data.models import CandleInterval, Candlestick, CandlestickSeries


def _series(n: int = 50) -> CandlestickSeries:
    candles = []
    px = 100.0
    start = 1_700_000_000_000
    for i in range(n):
        px += 0.6 if i < 30 else -1.0
        candles.append(
            Candlestick(
                openTime=start + i * 3_600_000,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px),
            )
        )
    return CandlestickSeries(
        symbol="btc_usdt",
        interval=CandleInterval.H1,
        candles=candles,
        retrievedAt=datetime.now(timezone.utc),
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/i.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    with patch("app.simulation.worker.ensure_worker_running"):
        with TestClient(app) as c:
            yield c


def test_pipeline_produces_decisions(client):
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_series())
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = client.post(
            "/backtest/runs",
            json={
                "symbol": "btc_usdt",
                "timeframe": "1h",
                "startTime": 1_700_000_000_000,
                "endTime": 1_700_000_000_000 + 60 * 3_600_000,
                "startingCapital": "1000",
                "allocatedCapital": "1000",
                "maxPositionSize": "1000",
                "strategyId": "dual_ema",
            },
        )
    assert r.status_code == 201
    assert r.json()["status"] == "completed"
    rid = r.json()["id"]
    decisions = client.get(f"/backtest/runs/{rid}/decisions").json()["decisions"]
    assert any(d["outcome"] == "hold" for d in decisions)
    assert any(d["signal"] in ("BUY", "SELL", "HOLD") for d in decisions)
