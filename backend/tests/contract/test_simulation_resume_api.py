"""Contract tests for POST /simulation/sessions/{id}/resume (Feature 014)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, SimulationSessionRow
from app.market_data.models import MarketQuote, MarketStatus
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
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
    mock_svc.get_candles = AsyncMock(side_effect=RuntimeError("unused"))
    with patch("app.simulation.session_service.get_market_data_service", return_value=mock_svc):
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock_svc):
            with patch("app.simulation.recovery.get_market_data_service", return_value=mock_svc):
                with patch("app.simulation.worker.ensure_worker_running"):
                    with TestClient(app) as c:
                        c.put("/portfolio/funding", json={"cash": "100000"})
                        yield c


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


def test_resume_invalid_state_stopped(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    client.post(f"/simulation/sessions/{sid}/start")
    client.post(f"/simulation/sessions/{sid}/stop")
    r = client.post(f"/simulation/sessions/{sid}/resume")
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "invalid_state_for_resume"


def test_resume_success_from_blocked(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "RECOVERY_BLOCKED"
        row.recovery_reason = "reconcile_mark_untrustworthy"
        row.cash = "500"
        row.position_side = "flat"
        row.position_qty = "0"
        row.position_flatten_status = "n/a"
        db.commit()
    finally:
        db.close()

    with patch(
        "app.simulation.session_service.apply_offline_gap_skip",
        new=AsyncMock(return_value=(True, None)),
        create=True,
    ):
        # Patch where resume imports from
        with patch(
            "app.simulation.gap_skip.apply_offline_gap_skip",
            new=AsyncMock(return_value=(True, None)),
        ):
            r = client.post(f"/simulation/sessions/{sid}/resume")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"] == "RUNNING"
    assert data["recoveryReason"] is None


def test_resume_still_blocked(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "RECOVERY_BLOCKED"
        row.cash = "499"  # G1 mismatch vs starting 500
        row.position_side = "flat"
        row.position_qty = "0"
        db.commit()
    finally:
        db.close()

    r = client.post(f"/simulation/sessions/{sid}/resume")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"]["code"] == "recovery_still_blocked"
    assert "failedGates" in detail["error"]
    assert detail["session"]["state"] == "RECOVERY_BLOCKED"


def test_active_includes_recovery_blocked(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "RECOVERY_BLOCKED"
        db.commit()
    finally:
        db.close()
    r = client.get("/simulation/sessions/active")
    assert r.status_code == 200
    body = r.json()
    assert body["session"] is not None
    assert body["session"]["id"] == sid
    assert body["session"]["state"] == "RECOVERY_BLOCKED"


def test_stop_from_recovery_blocked(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "RECOVERY_BLOCKED"
        db.commit()
    finally:
        db.close()
    r = client.post(f"/simulation/sessions/{sid}/stop")
    assert r.status_code == 200
    assert r.json()["state"] == "STOPPED"


def test_emergency_stop_from_recovery_blocked(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "RECOVERY_BLOCKED"
        db.commit()
    finally:
        db.close()
    r = client.post(f"/simulation/sessions/{sid}/emergency-stop")
    assert r.status_code == 200
    assert r.json()["state"] == "STOPPED"
    assert r.json()["stopReason"] == "emergency"
