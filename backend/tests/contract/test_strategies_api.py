"""Contract tests for GET /strategies."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/s.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    with TestClient(app) as c:
        yield c


def test_list_strategies_schema(client):
    r = client.get("/strategies")
    assert r.status_code == 200
    data = r.json()
    assert "strategies" in data
    assert len(data["strategies"]) == 8
    by_id = {s["id"]: s for s in data["strategies"]}
    assert set(by_id) == {
        "dual_ema",
        "rsi",
        "macd",
        "bollinger_bands",
        "breakout",
        "stochastic",
        "keltner_channel",
        "roc_momentum",
    }
    assert "volume" not in by_id
    assert not any("volume" in s["id"] for s in data["strategies"])

    dual = by_id["dual_ema"]
    assert dual["displayName"] == "Dual EMA"
    assert "dual_ema_9_21" in dual["aliases"]
    assert {p["name"] for p in dual["parameters"]} == {"fastPeriod", "slowPeriod"}

    rsi = by_id["rsi"]
    assert rsi["displayName"] == "RSI"
    assert {p["name"] for p in rsi["parameters"]} == {"period", "overbought", "oversold"}
    assert any(c["code"] == "oversold_lt_overbought" for c in rsi["constraints"])

    macd = by_id["macd"]
    assert macd["displayName"] == "MACD"
    assert {p["name"] for p in macd["parameters"]} == {
        "fastPeriod",
        "slowPeriod",
        "signalPeriod",
    }

    bollinger = by_id["bollinger_bands"]
    assert bollinger["displayName"] == "Bollinger Bands"
    std_dev = next(p for p in bollinger["parameters"] if p["name"] == "stdDev")
    assert std_dev["type"] == "decimal_string"
    assert std_dev.get("exclusiveMinimum") is True

    breakout = by_id["breakout"]
    assert breakout["displayName"] == "Breakout"
    assert {p["name"] for p in breakout["parameters"]} == {"lookback"}

    stoch = by_id["stochastic"]
    assert stoch["displayName"] == "Stochastic"
    assert {p["name"] for p in stoch["parameters"]} == {
        "kPeriod",
        "dPeriod",
        "overbought",
        "oversold",
    }

    keltner = by_id["keltner_channel"]
    assert keltner["displayName"] == "Keltner Channel"
    assert {p["name"] for p in keltner["parameters"]} == {"emaPeriod", "atrPeriod", "atrMult"}

    roc = by_id["roc_momentum"]
    assert roc["displayName"] == "ROC Momentum"
    assert {p["name"] for p in roc["parameters"]} == {
        "period",
        "buyThreshold",
        "sellThreshold",
    }
