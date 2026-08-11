"""Contract tests for simulation API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.market_data.models import MarketQuote, MarketStatus
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

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

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=_quote)
    with patch("app.simulation.session_service.get_market_data_service", return_value=mock_svc):
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock_svc):
            with patch("app.simulation.worker.ensure_worker_running"):
                with TestClient(app) as c:
                    yield c


def test_journals_and_economics_shape(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    assert "economics" in created
    assert "netPnl" in created["economics"]
    assert "markEquity" in created["economics"]
    d = client.get(f"/simulation/sessions/{sid}/decisions")
    assert d.status_code == 200
    assert d.json()["items"] == []
    t = client.get(f"/simulation/sessions/{sid}/trades")
    assert t.status_code == 200
    assert t.json()["items"] == []


def test_stop_manual(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    client.post(f"/simulation/sessions/{created['id']}/start")
    stopped = client.post(f"/simulation/sessions/{created['id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "STOPPED"
    assert stopped.json()["stopReason"] == "manual"


def test_create_accepts_1m_and_5m_timeframes(client):
    for tf in ("1m", "5m"):
        r = client.post("/simulation/sessions", json=_body(timeframe=tf))
        assert r.status_code == 201, r.text
        assert r.json()["timeframe"] == tf


def test_create_rejects_unsupported_timeframe(client):
    r = client.post("/simulation/sessions", json=_body(timeframe="3m"))
    assert r.status_code == 400


def _body(**over):
    base = {
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
    }
    base.update(over)
    return base


def test_create_requires_strategy_id(client):
    body = _body()
    del body["strategyId"]
    r = client.post("/simulation/sessions", json=body)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] in ("missing_strategy", "invalid_config")


def test_alias_persists_canonical(client):
    r = client.post("/simulation/sessions", json=_body(strategyId="dual_ema_9_21"))
    assert r.status_code == 201
    data = r.json()
    assert data["strategyId"] == "dual_ema"
    assert data["strategyParams"] == {"fastPeriod": 9, "slowPeriod": 21}


def test_invalid_strategy_params_message(client):
    r = client.post(
        "/simulation/sessions",
        json=_body(strategyParams={"fastPeriod": 30, "slowPeriod": 21}),
    )
    assert r.status_code == 400
    assert "Fast period must be less than slow period." in r.json()["detail"]["error"]["message"]


def test_create_derives_amounts(client):
    r = client.post("/simulation/sessions", json=_body())
    assert r.status_code == 201
    data = r.json()
    assert data["targetNetProfitAmount"] == "5"
    assert data["maxSessionLossAmount"] == "3.5"
    assert data["label"] == "SIMULATION"
    assert data["state"] == "CONFIGURED"


def test_reject_real_money(client):
    r = client.post("/simulation/sessions", json=_body(mode="real_money"))
    assert r.status_code == 400


def test_reject_bad_capital_nesting(client):
    r = client.post(
        "/simulation/sessions",
        json=_body(startingCapital="100", allocatedCapital="200", maxPositionSize="50"),
    )
    assert r.status_code == 400


def test_start_and_active(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    started = client.post(f"/simulation/sessions/{created['id']}/start")
    assert started.status_code == 200
    assert started.json()["state"] == "RUNNING"
    active = client.get("/simulation/sessions/active")
    assert active.json()["session"]["id"] == created["id"]
    other = client.post("/simulation/sessions", json=_body()).json()
    r2 = client.post(f"/simulation/sessions/{other['id']}/start")
    assert r2.status_code == 409
