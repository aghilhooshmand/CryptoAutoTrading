"""Contract tests for Feature 008 /settings API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.settings.starters import product_starter_defaults
from app.market_data.identity import is_xt_form_symbol


_KRAKEN_IDENTITY_KEYS = (
    "venue",
    "baseAsset",
    "quoteAsset",
    "canonicalSymbol",
    "venueProductId",
)


def _valid_body(**overrides):
    body = product_starter_defaults()
    symbol = overrides.get("symbol")
    if symbol and is_xt_form_symbol(str(symbol)):
        for key in _KRAKEN_IDENTITY_KEYS:
            body.pop(key, None)
    body.update(overrides)
    return body


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/s.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    with TestClient(app) as c:
        yield c


def test_get_empty_returns_starters(client):
    r = client.get("/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "starters"
    assert data["symbol"] == "BTC/EUR"
    assert data["venue"] == "kraken"
    assert data["startingCapital"] == "1000"
    assert data["strategyId"] == "dual_ema"
    assert data["decisionLogMode"] == "important_only"
    assert data["warning"] is None


def test_put_valid_save(client):
    body = _valid_body(symbol="eth_usdt", startingCapital="2000", allocatedCapital="2000", maxPositionSize="1000")
    r = client.put("/settings", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "saved"
    assert data["symbol"] == "eth_usdt"
    assert data["updatedAt"]

    again = client.get("/settings").json()
    assert again["symbol"] == "eth_usdt"
    assert again["source"] == "saved"


def test_put_invalid_nesting_leaves_prior(client):
    client.put("/settings", json=_valid_body(symbol="eth_usdt"))
    bad = _valid_body(symbol="sol_usdt", maxPositionSize="9000")
    r = client.put("/settings", json=bad)
    assert r.status_code == 400
    err = r.json()["detail"]["error"]
    assert err["code"] == "invalid_config"

    again = client.get("/settings").json()
    assert again["symbol"] == "eth_usdt"


def test_put_invalid_strategy_params(client):
    body = _valid_body(strategyId="rsi", strategyParams={"period": 14, "overbought": 20, "oversold": 80})
    r = client.put("/settings", json=body)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] in {"invalid_strategy_params", "invalid_config"}


def test_optional_nulls_persist(client):
    body = _valid_body(targetNetProfitRate=None, maxSessionLossRate=None, maxTrades=None)
    r = client.put("/settings", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["targetNetProfitRate"] is None
    assert data["maxSessionLossRate"] is None
    assert data["maxTrades"] is None


def test_put_decision_log_mode(client):
    body = _valid_body(decisionLogMode="full_audit")
    r = client.put("/settings", json=body)
    assert r.status_code == 200
    assert r.json()["decisionLogMode"] == "full_audit"
    again = client.get("/settings").json()
    assert again["decisionLogMode"] == "full_audit"


def test_reset_restores_starters(client):
    client.put(
        "/settings",
        json=_valid_body(
            symbol="eth_usdt",
            startingCapital="2500",
            allocatedCapital="2500",
            maxPositionSize="1000",
        ),
    )
    r = client.post("/settings/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "BTC/EUR"
    assert data["venue"] == "kraken"
    assert data["canonicalSymbol"] == "BTC/EUR"
    assert data["venueProductId"] == "XXBTZEUR"
    assert data["startingCapital"] == "1000"
    assert data["decisionLogMode"] == "important_only"
    assert data["source"] == "saved"
    assert data["updatedAt"]
