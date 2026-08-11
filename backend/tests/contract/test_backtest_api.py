"""Contract tests for /backtest API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, BacktestRunRow
from app.main import app
from app.market_data.models import CandleInterval, Candlestick, CandlestickSeries


def _candles(n: int, start: int = 1_700_000_000_000, step: int = 3_600_000) -> list[Candlestick]:
    out = []
    px = 100.0
    for i in range(n):
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px + (0.5 if i % 2 == 0 else -0.3)),
            )
        )
        px += 0.2 if i % 5 != 0 else -0.5
    return out


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/bt.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    with patch("app.simulation.worker.ensure_worker_running"):
        with TestClient(app) as c:
            yield c, TestingSession


def _body(**over):
    base = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_000_000 + 30 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
    }
    base.update(over)
    return base


def _mock_series(n: int):
    now = datetime.now(timezone.utc)
    return CandlestickSeries(
        symbol="btc_usdt",
        interval=CandleInterval.H1,
        candles=_candles(n),
        retrievedAt=now,
    )


def test_invalid_config_no_row(client):
    c, Session = client
    r = c.post("/backtest/runs", json=_body(startingCapital="100", maxPositionSize="500"))
    assert r.status_code == 400
    detail = r.json()["detail"]["error"]
    assert detail["code"] == "invalid_config"
    db = Session()
    assert db.scalars(select(BacktestRunRow)).first() is None
    db.close()


def test_oversized_no_row(client):
    c, Session = client
    r = c.post(
        "/backtest/runs",
        json=_body(endTime=1_700_000_000_000 + 6000 * 3_600_000),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "oversized_history"
    db = Session()
    assert db.scalars(select(BacktestRunRow)).first() is None
    db.close()


def test_insufficient_history_failed_row(client):
    c, Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(10))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post("/backtest/runs", json=_body())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "failed"
    assert body["errorCode"] == "insufficient_history"
    db = Session()
    row = db.scalars(select(BacktestRunRow)).first()
    assert row is not None and row.status == "failed"
    db.close()


def test_successful_run_summary(client):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(40))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post("/backtest/runs", json=_body())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["summary"] is not None
    assert "netPnl" in body["summary"]
    assert "startingCapital" in body["summary"]
    rid = body["id"]
    trades = c.get(f"/backtest/runs/{rid}/trades")
    decisions = c.get(f"/backtest/runs/{rid}/decisions")
    assert trades.status_code == 200
    assert decisions.status_code == 200
    assert len(decisions.json()["decisions"]) >= 21
