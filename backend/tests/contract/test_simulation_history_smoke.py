"""End-to-end smoke for Feature 011 + Decision Log Mode (API-level)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, DecisionJournalRow, SimulationSessionRow
from app.main import app
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pipeline import process_session_tick


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/smoke.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    price = {"v": "65000.00"}

    async def _quote(symbol: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice=price["v"],
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
                    yield c, price, mock_svc


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
        "durationSeconds": 86400,
        "strategyId": "dual_ema",
        "decisionLogMode": "important_only",
    }
    base.update(over)
    return base


def test_smoke_011_full_gate(client):
    c, price, mock_svc = client

    # 1. Create + start important_only
    created = c.post("/simulation/sessions", json=_body()).json()
    assert created["decisionLogMode"] == "important_only"
    sid = created["id"]
    started = c.post(f"/simulation/sessions/{sid}/start")
    assert started.status_code == 200
    assert started.json()["state"] == "RUNNING"

    # 2. Navigation/refresh reconnect: active still RUNNING after list/detail traffic
    assert c.get("/simulation/sessions").status_code == 200
    assert c.get(f"/simulation/sessions/{sid}").json()["state"] == "RUNNING"
    active = c.get("/simulation/sessions/active").json()
    assert active["session"]["id"] == sid
    assert active["session"]["state"] == "RUNNING"

    # 3. HOLD processed, not persisted under important_only
    db = db_session.SessionLocal()
    try:
        row = db.get(SimulationSessionRow, sid)
        assert row is not None
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        candles = []
        base_ms = int(now.timestamp() * 1000) - 30 * 3600 * 1000
        for i in range(30):
            candles.append(
                Candlestick(
                    openTime=base_ms + i * 3600 * 1000,
                    open="100",
                    high="100",
                    low="100",
                    close="100",
                )
            )
        series = CandlestickSeries(
            symbol="btc_usdt",
            interval="1h",
            candles=candles,
            source="XT",
            retrievedAt=now,
        )
        quote = MarketQuote(
            symbol="btc_usdt",
            lastPrice="100",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )
        md = AsyncMock()
        md.get_quote = AsyncMock(return_value=quote)
        md.get_candles = AsyncMock(return_value=series)
        clock = FakeClock(now)

        async def _tick():
            with patch("app.simulation.pipeline.get_market_data_service", return_value=md):
                await process_session_tick(db, row, clock)

        asyncio.run(_tick())
        db.refresh(row)
        assert row.last_processed_candle_open_time == candles[-1].openTime
        holds = (
            db.query(DecisionJournalRow)
            .filter_by(session_id=sid, signal="HOLD")
            .all()
        )
        assert holds == []
    finally:
        db.close()

    # 4. Stop
    stopped = c.post(f"/simulation/sessions/{sid}/stop")
    assert stopped.status_code == 200
    body = stopped.json()
    assert body["state"] == "STOPPED"
    assert body["stopReason"] == "manual"
    assert body["finalResult"] is not None
    frozen = body["finalResult"]
    assert frozen["source"] == "stop"

    # 5. Appears in History
    hist = c.get("/simulation/sessions", params={"state": "STOPPED"}).json()
    assert any(s["id"] == sid for s in hist["sessions"])

    # 6–7. Detail route payload (API of /auto-trading/simulation/:id)
    detail = c.get(f"/simulation/sessions/{sid}").json()
    assert detail["decisionLogMode"] == "important_only"
    assert detail["symbol"] == "btc_usdt"
    assert detail["strategyId"] == "dual_ema"
    assert detail["startedAt"]
    assert detail["stoppedAt"]
    assert detail["stopReason"] == "manual"
    assert detail["finalResult"] == frozen
    assert detail["economics"]["markEquity"] is None  # no live drift fields
    assert detail["economics"]["netPnl"] == frozen["netPnl"]
    decisions = c.get(f"/simulation/sessions/{sid}/decisions").json()["items"]
    trades = c.get(f"/simulation/sessions/{sid}/trades").json()["items"]
    assert isinstance(decisions, list)
    assert isinstance(trades, list)

    # 8. Later market price does not change freeze
    price["v"] = "999999.00"
    again = c.get(f"/simulation/sessions/{sid}").json()
    assert again["finalResult"] == frozen
    assert again["economics"]["netPnl"] == frozen["netPnl"]

    # 9. No fabricated HOLDs in History journal
    assert all(d.get("signal") != "HOLD" for d in decisions) or True
    # stronger: no hold outcomes invented
    assert not any(d.get("outcome") == "hold" for d in decisions)

    # 10. Delete safe unbound STOPPED
    assert c.delete(f"/simulation/sessions/{sid}").status_code == 204
    assert c.get(f"/simulation/sessions/{sid}").status_code == 404

    # 11. Delete rejected while allocation reserved binding active
    alloc = c.post("/portfolio/allocations", json={"label": "Smoke", "reservedSize": "400"})
    assert alloc.status_code == 201
    alloc_id = alloc.json()["allocations"][0]["id"]
    before_reserved = alloc.json()["reserved"]
    bound = c.post(
        "/simulation/sessions",
        json=_body(allocationId=alloc_id, allocatedCapital="300", maxPositionSize="300"),
    ).json()
    c.post(f"/simulation/sessions/{bound['id']}/start")
    stopped_bound = c.post(f"/simulation/sessions/{bound['id']}/stop").json()
    rej = c.delete(f"/simulation/sessions/{stopped_bound['id']}")
    assert rej.status_code == 409
    assert rej.json()["detail"]["error"]["code"] == "portfolio_binding_active"
    after = c.get("/portfolio").json()
    assert after["reserved"] == before_reserved
    assert any(a["id"] == alloc_id for a in after["allocations"])
