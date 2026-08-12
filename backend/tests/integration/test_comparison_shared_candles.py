"""Integration: shared candles yield deterministic multi-leg comparison metrics."""

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
        f"sqlite:///{tmp_path}/cmp_int.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    with patch("app.simulation.worker.ensure_worker_running"):
        with TestClient(app) as c:
            yield c


def test_shared_fixture_deterministic_metrics(client):
    candles = _candles(50)
    series = CandlestickSeries(
        symbol="btc_usdt",
        interval=CandleInterval.H1,
        candles=candles,
        retrievedAt=datetime.now(timezone.utc),
    )
    body = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_000_000 + 50 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "legs": [
            {"strategyId": "dual_ema"},
            {"strategyId": "rsi"},
        ],
    }
    with patch("app.comparison.service.get_market_data_service") as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        first = client.post("/comparisons", json=body).json()
        second = client.post("/comparisons", json=body).json()

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["buyAndHoldReturnPct"] == second["buyAndHoldReturnPct"]
    assert first["candleCount"] == second["candleCount"] == 50
    for a, b in zip(first["legs"], second["legs"], strict=True):
        assert a["strategyId"] == b["strategyId"]
        assert a["netPnl"] == b["netPnl"]
        assert a["returnPct"] == b["returnPct"]
        assert a["fillCount"] == b["fillCount"]
        assert a["roundTripCount"] == b["roundTripCount"]
        assert a["vsBuyAndHoldReturnPct"] == b["vsBuyAndHoldReturnPct"]
        assert a["buyAndHoldReturnPct"] == first["buyAndHoldReturnPct"]
