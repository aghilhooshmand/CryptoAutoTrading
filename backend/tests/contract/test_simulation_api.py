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
                    # Feature 010: create/start require Portfolio available ≥ allocated.
                    c.put("/portfolio/funding", json={"cash": "100000"})
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


@pytest.mark.parametrize(
    ("strategy_id", "params", "expected_params"),
    [
        ("rsi", None, {"period": 14, "overbought": 70, "oversold": 30}),
        ("macd", None, {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}),
        (
            "bollinger_bands",
            None,
            {"period": 20, "stdDev": "2.0"},
        ),
        ("breakout", None, {"lookback": 20}),
    ],
)
def test_create_accepts_new_strategies(client, strategy_id, params, expected_params):
    body = _body(strategyId=strategy_id)
    if params is not None:
        body["strategyParams"] = params
    r = client.post("/simulation/sessions", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["strategyId"] == strategy_id
    assert data["strategyParams"] == expected_params


@pytest.mark.parametrize(
    ("strategy_id", "params", "message_part"),
    [
        (
            "rsi",
            {"period": 14, "overbought": 30, "oversold": 70},
            "Oversold threshold must be less than overbought threshold.",
        ),
        (
            "macd",
            {"fastPeriod": 26, "slowPeriod": 12, "signalPeriod": 9},
            "Fast period must be less than slow period.",
        ),
        (
            "bollinger_bands",
            {"period": 20, "stdDev": "0"},
            "must be > 0",
        ),
        ("breakout", {"lookback": 1}, "lookback"),
    ],
)
def test_invalid_new_strategy_params(client, strategy_id, params, message_part):
    r = client.post(
        "/simulation/sessions",
        json=_body(strategyId=strategy_id, strategyParams=params),
    )
    assert r.status_code == 400
    assert message_part in r.json()["detail"]["error"]["message"]


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


def test_create_rejects_when_allocated_exceeds_available(client):
    # Fixture funds 100000; reserve most so available < 500.
    client.put("/portfolio/funding", json={"cash": "1000"})
    client.post(
        "/portfolio/allocations",
        json={"label": "sleeve", "reservedSize": "400"},
    )
    r = client.post(
        "/simulation/sessions",
        json=_body(startingCapital="700", allocatedCapital="700", maxPositionSize="700"),
    )
    assert r.status_code == 400
    err = r.json()["detail"]["error"]
    assert err["code"] == "insufficient_portfolio_available"
    assert "available" in err["message"].lower()


def test_create_ok_when_allocated_fits_available(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    client.post(
        "/portfolio/allocations",
        json={"label": "sleeve", "reservedSize": "400"},
    )
    r = client.post(
        "/simulation/sessions",
        json=_body(startingCapital="600", allocatedCapital="600", maxPositionSize="600"),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["allocatedCapital"] == "600"


def test_create_persists_optional_risk_fields(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    alloc = client.post(
        "/portfolio/allocations",
        json={"label": "bound", "reservedSize": "200"},
    ).json()["allocations"][0]
    r = client.post(
        "/simulation/sessions",
        json=_body(
            startingCapital="200",
            allocatedCapital="200",
            maxPositionSize="200",
            allocationId=alloc["id"],
            portfolioMaxLossRate="0.05",
            perSymbolMaxWeight="0.25",
        ),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["allocationId"] == alloc["id"]
    assert data["portfolioMaxLossRate"] == "0.05"
    assert data["perSymbolMaxWeight"] == "0.25"


def test_start_rejects_when_available_shrunk(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    created = client.post(
        "/simulation/sessions",
        json=_body(startingCapital="600", allocatedCapital="600", maxPositionSize="600"),
    ).json()
    client.post(
        "/portfolio/allocations",
        json={"label": "later", "reservedSize": "500"},
    )
    r = client.post(f"/simulation/sessions/{created['id']}/start")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "insufficient_portfolio_available"


def test_start_freezes_portfolio_loss_baseline(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    created = client.post(
        "/simulation/sessions",
        json=_body(
            startingCapital="500",
            allocatedCapital="500",
            maxPositionSize="500",
            portfolioMaxLossRate="0.1",
        ),
    ).json()
    started = client.post(f"/simulation/sessions/{created['id']}/start")
    assert started.status_code == 200, started.text
    data = started.json()
    assert data["portfolioLossBaselineKind"] in ("equity", "quote_cash")
    assert data["portfolioLossBaselineValue"] is not None
    assert data["portfolioMaxLossAmount"] is not None
