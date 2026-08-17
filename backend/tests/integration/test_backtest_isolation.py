"""Isolation: backtest does not mutate simulation session."""

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
from app.market_data.models import CandleInterval, Candlestick, CandlestickSeries, MarketQuote, MarketStatus


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/iso.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    async def _quote(symbol: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    mock_sim = AsyncMock()
    mock_sim.get_quote = AsyncMock(side_effect=_quote)
    candles = [
        Candlestick(openTime=1_700_000_000_000 + i * 3_600_000, open="100", high="101", low="99", close="100")
        for i in range(30)
    ]
    mock_bt = AsyncMock()
    mock_bt.get_candles = AsyncMock(
        return_value=CandlestickSeries(
            symbol="btc_usdt",
            interval=CandleInterval.H1,
            candles=candles,
            retrievedAt=datetime.now(timezone.utc),
        )
    )

    with patch("app.simulation.session_service.get_market_data_service", return_value=mock_sim):
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock_sim):
            with patch("app.backtest.service.get_market_data_service", return_value=mock_bt):
                with patch("app.simulation.worker.ensure_worker_running"):
                    with TestClient(app) as c:
                        c.put("/portfolio/funding", json={"cash": "100000"})
                        yield c


def test_backtest_does_not_change_simulation_cash(client):
    created = client.post(
        "/simulation/sessions",
        json={
            "mode": "simulation",
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startingCapital": "500",
            "allocatedCapital": "500",
            "maxPositionSize": "500",
            "targetNetProfitRate": "0.01",
            "maxSessionLossRate": "0.007",
            "maxTrades": 20,
            "durationSeconds": 3600,
            "strategyId": "dual_ema",
        },
    )
    assert created.status_code == 201
    sid = created.json()["id"]
    cash_before = created.json()["cash"]
    client.post(f"/simulation/sessions/{sid}/start")
    bt = client.post(
        "/backtest/runs",
        json={
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startTime": 1_700_000_000_000,
            "endTime": 1_700_000_000_000 + 40 * 3_600_000,
            "startingCapital": "1000",
            "allocatedCapital": "1000",
            "maxPositionSize": "1000",
            "strategyId": "dual_ema",
        },
    )
    assert bt.status_code == 201
    sim = client.get(f"/simulation/sessions/{sid}")
    assert sim.json()["cash"] == cash_before
