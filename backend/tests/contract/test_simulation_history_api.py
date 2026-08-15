"""Contract tests for Feature 011 Simulation History API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, DecisionJournalRow, SimulationSessionRow
from app.main import app
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.final_result import parse_final_result


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/h.db", connect_args={"check_same_thread": False})
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
        "decisionLogMode": "important_only",
    }
    base.update(over)
    return base


def _create_stopped(client, **over):
    created = client.post("/simulation/sessions", json=_body(**over)).json()
    client.post(f"/simulation/sessions/{created['id']}/start")
    stopped = client.post(f"/simulation/sessions/{created['id']}/stop")
    assert stopped.status_code == 200, stopped.text
    return stopped.json()


def test_list_order_and_pagination(client):
    ids = []
    for i in range(3):
        s = _create_stopped(client)
        ids.append(s["id"])

    r = client.get("/simulation/sessions", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert data["totalCount"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["sessions"]) == 2
    # newest first
    assert data["sessions"][0]["id"] == ids[-1]
    assert data["sessions"][1]["id"] == ids[-2]

    page2 = client.get("/simulation/sessions", params={"limit": 2, "offset": 2}).json()
    assert len(page2["sessions"]) == 1
    assert page2["sessions"][0]["id"] == ids[0]


def test_list_state_filter_and_invalid_query(client):
    _create_stopped(client)
    configured = client.post("/simulation/sessions", json=_body()).json()

    stopped_only = client.get("/simulation/sessions", params={"state": "STOPPED"}).json()
    assert all(s["state"] == "STOPPED" for s in stopped_only["sessions"])
    assert stopped_only["totalCount"] >= 1

    cfg = client.get("/simulation/sessions", params={"state": "CONFIGURED"}).json()
    assert any(s["id"] == configured["id"] for s in cfg["sessions"])

    bad = client.get("/simulation/sessions", params={"state": "DONE"})
    assert bad.status_code == 400
    assert bad.json()["detail"]["error"]["code"] == "invalid_query"

    assert client.get("/simulation/sessions", params={"limit": 101}).status_code == 400
    assert client.get("/simulation/sessions", params={"offset": -1}).status_code == 400


def test_detail_has_final_result_after_stop(client):
    stopped = _create_stopped(client)
    assert stopped["finalResult"] is not None
    assert stopped["finalResult"]["source"] == "stop"
    assert stopped["economics"]["markEquity"] is None
    assert stopped["economics"]["markNetPnl"] is None

    again = client.get(f"/simulation/sessions/{stopped['id']}").json()
    assert again["finalResult"]["netPnl"] == stopped["finalResult"]["netPnl"]
    assert again["decisionLogMode"] == "important_only"


def test_final_result_immutable_when_quote_changes(client):
    stopped = _create_stopped(client)
    frozen = stopped["finalResult"]
    assert frozen is not None

    async def _expensive(symbol: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="999999.00",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    with patch(
        "app.simulation.session_service.get_market_data_service",
        return_value=AsyncMock(get_quote=AsyncMock(side_effect=_expensive)),
    ):
        again = client.get(f"/simulation/sessions/{stopped['id']}").json()
    assert again["finalResult"] == frozen
    assert again["economics"]["netPnl"] == frozen["netPnl"]


def test_ledger_backfill_on_detail_for_legacy_stopped(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    sid = created["id"]
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        row.state = "STOPPED"
        row.stop_reason = "manual"
        row.stopped_at = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        row.cash = "510"
        row.position_side = "flat"
        row.position_qty = "0"
        row.final_result_json = None
        db.commit()
    finally:
        db.close()

    detail = client.get(f"/simulation/sessions/{sid}").json()
    assert detail["finalResult"] is not None
    assert detail["finalResult"]["source"] == "backfill"
    assert detail["finalResult"]["complete"] is True
    assert detail["finalResult"]["endingEquity"] == "510"


def test_delete_cascade_and_rejects(client):
    stopped = _create_stopped(client)
    sid = stopped["id"]
    # seed a decision row
    db = db_session.SessionLocal()
    try:
        db.add(
            DecisionJournalRow(
                id="22222222-2222-2222-2222-222222222222",
                session_id=sid,
                created_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
                candle_open_time=1,
                signal="BUY",
                outcome="rejected",
                reason_code="maximum_trades_reached",
                reason_message="max",
                fast_ema=None,
                slow_ema=None,
            )
        )
        db.commit()
    finally:
        db.close()

    assert client.get(f"/simulation/sessions/{sid}/decisions").json()["items"]
    r = client.delete(f"/simulation/sessions/{sid}")
    assert r.status_code == 204
    assert client.get(f"/simulation/sessions/{sid}").status_code == 404
    assert client.get(f"/simulation/sessions/{sid}/decisions").status_code == 404

    running = client.post("/simulation/sessions", json=_body()).json()
    client.post(f"/simulation/sessions/{running['id']}/start")
    rej = client.delete(f"/simulation/sessions/{running['id']}")
    assert rej.status_code == 409
    assert rej.json()["detail"]["error"]["code"] == "session_active"


def test_delete_rejects_portfolio_binding_without_unwind(client):
    alloc = client.post(
        "/portfolio/allocations",
        json={"label": "A", "reservedSize": "400"},
    )
    assert alloc.status_code == 201, alloc.text
    portfolio = alloc.json()
    alloc_id = portfolio["allocations"][0]["id"]
    before_reserved = portfolio["reserved"]

    created = client.post(
        "/simulation/sessions",
        json=_body(allocationId=alloc_id, allocatedCapital="300", maxPositionSize="300"),
    ).json()
    client.post(f"/simulation/sessions/{created['id']}/start")
    stopped = client.post(f"/simulation/sessions/{created['id']}/stop").json()

    rej = client.delete(f"/simulation/sessions/{stopped['id']}")
    assert rej.status_code == 409
    assert rej.json()["detail"]["error"]["code"] == "portfolio_binding_active"

    after = client.get("/portfolio").json()
    assert after["reserved"] == before_reserved
    assert any(a["id"] == alloc_id for a in after["allocations"])


def test_active_still_running_after_list_traffic(client):
    created = client.post("/simulation/sessions", json=_body()).json()
    client.post(f"/simulation/sessions/{created['id']}/start")
    client.get("/simulation/sessions")
    client.get(f"/simulation/sessions/{created['id']}")
    active = client.get("/simulation/sessions/active").json()
    assert active["session"] is not None
    assert active["session"]["state"] == "RUNNING"
    assert active["session"]["id"] == created["id"]


def test_no_resume_endpoint_for_stopped(client):
    stopped = _create_stopped(client)
    # FR-020: no resume/restart of historical session id
    assert client.post(f"/simulation/sessions/{stopped['id']}/resume").status_code == 404
    restart = client.post(f"/simulation/sessions/{stopped['id']}/start")
    assert restart.status_code == 409


def test_important_only_history_journal_no_fabricated_holds(client):
    stopped = _create_stopped(client, decisionLogMode="important_only")
    detail = client.get(f"/simulation/sessions/{stopped['id']}").json()
    assert detail["decisionLogMode"] == "important_only"
    decisions = client.get(f"/simulation/sessions/{stopped['id']}/decisions").json()["items"]
    assert all(d["signal"] != "HOLD" or d["outcome"] != "hold" for d in decisions) or decisions == []


def test_full_audit_mode_visible_on_detail(client):
    stopped = _create_stopped(client, decisionLogMode="full_audit")
    detail = client.get(f"/simulation/sessions/{stopped['id']}").json()
    assert detail["decisionLogMode"] == "full_audit"


def test_recovery_freezes_orphan(client):
    from app.simulation.recovery import recover_orphan_sessions

    created = client.post("/simulation/sessions", json=_body()).json()
    client.post(f"/simulation/sessions/{created['id']}/start")
    db = db_session.SessionLocal()
    try:
        n = recover_orphan_sessions(db)
        assert n == 1
        row = db.get(SimulationSessionRow, created["id"])
        assert row is not None
        assert row.state == "STOPPED"
        assert row.stop_reason == "backend_restart"
        fr = parse_final_result(row.final_result_json)
        assert fr is not None
        assert fr["source"] == "recovery"
    finally:
        db.close()
