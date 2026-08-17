"""Contract tests for Controlled Real session create (Feature 015)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.real_gates import set_try_free_usdt_override


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    set_try_free_usdt_override(lambda: Decimal("100"))

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
                    c.put("/portfolio/funding", json={"cash": "100000"})
                    yield c
    set_try_free_usdt_override(None)


def _real_body(**over):
    base = {
        "mode": "real",
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "allocatedCapital": "25",
        "maxPositionSize": "25",
        "targetNetProfitRate": "0.01",
        "maxSessionLossRate": "0.007",
        "maxTrades": 20,
        "durationSeconds": 3600,
        "strategyId": "dual_ema",
    }
    base.update(over)
    return base


def test_real_create_rejects_over_50(client):
    r = client.post("/simulation/sessions", json=_real_body(allocatedCapital="51", maxPositionSize="51"))
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "real_capital_cap_exceeded"


def test_real_create_ok_returns_mode_real(client):
    before = client.get("/portfolio").json()
    holdings_before = {(h.get("asset"), h.get("quantity") or h.get("free") or h.get("total")) for h in before.get("holdings", [])}

    r = client.post("/simulation/sessions", json=_real_body())
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["mode"] == "real"
    assert data["label"] == "REAL"
    assert data["allocatedCapital"] == "25"
    assert data["startingCapital"] == "25"
    assert data["cashIsLocalBudgetOnly"] is True
    assert data["allocationId"] is None

    after = client.get("/portfolio").json()
    holdings_after = {(h.get("asset"), h.get("quantity") or h.get("free") or h.get("total")) for h in after.get("holdings", [])}
    assert holdings_after == holdings_before


def test_real_create_requires_credentials(client, monkeypatch):
    monkeypatch.delenv("XT_API_KEY", raising=False)
    monkeypatch.delenv("XT_API_SECRET", raising=False)
    r = client.post("/simulation/sessions", json=_real_body())
    assert r.status_code == 503
    assert r.json()["detail"]["error"]["code"] == "credentials_missing"


def test_real_create_insufficient_xt_free(client):
    set_try_free_usdt_override(lambda: Decimal("10"))
    try:
        r = client.post("/simulation/sessions", json=_real_body(allocatedCapital="25", maxPositionSize="25"))
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "insufficient_xt_free"
    finally:
        set_try_free_usdt_override(lambda: Decimal("100"))


def _start_real(client):
    created = client.post("/simulation/sessions", json=_real_body())
    assert created.status_code == 201, created.text
    sid = created.json()["id"]
    started = client.post(f"/simulation/sessions/{sid}/start")
    assert started.status_code == 200, started.text
    return sid


def test_decline_entry_no_pending(client):
    sid = _start_real(client)
    r = client.post(f"/simulation/sessions/{sid}/decline-entry")
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "no_pending_confirmation"


def test_decline_entry_ok(client):
    from datetime import datetime, timezone

    from app.db import session as db_session
    from app.simulation.pending_confirmation import create_pending

    sid = _start_real(client)
    db = db_session.SessionLocal()
    try:
        create_pending(
            db,
            session_id=sid,
            symbol="btc_usdt",
            proposed_notional="25",
            reference_price="65000",
            now=datetime.now(timezone.utc),
        )
        db.commit()
    finally:
        db.close()

    r = client.post(f"/simulation/sessions/{sid}/decline-entry")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["pendingConfirmation"] is None
    assert data["state"] == "RUNNING"


def test_confirm_entry_expired_pending(client):
    from datetime import datetime, timedelta, timezone

    from app.db import session as db_session
    from app.db.models import PendingEntryConfirmationRow

    sid = _start_real(client)
    db = db_session.SessionLocal()
    try:
        row = (
            db.query(PendingEntryConfirmationRow)
            .filter(PendingEntryConfirmationRow.session_id == sid)
            .first()
        )
        if row is None:
            from app.simulation.pending_confirmation import create_pending

            row = create_pending(
                db,
                session_id=sid,
                symbol="btc_usdt",
                proposed_notional="25",
                reference_price="65000",
                now=datetime.now(timezone.utc) - timedelta(minutes=6),
            )
        else:
            row.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    r = client.post(f"/simulation/sessions/{sid}/confirm-entry")
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "pending_confirmation_expired"
