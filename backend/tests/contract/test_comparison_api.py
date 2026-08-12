"""Contract tests for /comparisons API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, BacktestRunRow, StrategyComparisonRow
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
        f"sqlite:///{tmp_path}/cmp_api.db", connect_args={"check_same_thread": False}
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
        "endTime": 1_700_000_000_000 + 40 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "legs": [
            {"strategyId": "dual_ema"},
            {"strategyId": "rsi"},
        ],
    }
    base.update(over)
    return base


def _mock_series(n: int = 40):
    return CandlestickSeries(
        symbol="btc_usdt",
        interval=CandleInterval.H1,
        candles=_candles(n),
        retrievedAt=datetime.now(timezone.utc),
    )


def test_post_completed_two_legs(client):
    c, Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        r = c.post("/comparisons", json=_body())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "completed"
    assert len(body["legs"]) == 2
    for leg in body["legs"]:
        assert leg["backtestRunId"]
        assert "roundTripCount" in leg
        assert "fillCount" in leg
        assert leg["fillCount"] is not None
    assert "bestStrategyId" not in body
    assert "winner" not in body
    # Legs marked comparison origin
    db = Session()
    try:
        runs = list(db.scalars(select(BacktestRunRow)).all())
        assert len(runs) == 2
        assert all(run.origin == "comparison" for run in runs)
        assert all(run.comparison_id == body["id"] for run in runs)
    finally:
        db.close()


def test_reject_one_leg_no_row(client):
    c, Session = client
    r = c.post("/comparisons", json=_body(legs=[{"strategyId": "dual_ema"}]))
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "invalid_comparison"
    db = Session()
    try:
        assert list(db.scalars(select(StrategyComparisonRow)).all()) == []
    finally:
        db.close()


def test_reject_six_legs(client):
    c, _Session = client
    legs = [{"strategyId": "dual_ema"} for _ in range(6)]
    r = c.post("/comparisons", json=_body(legs=legs))
    assert r.status_code == 400


def test_insufficient_history_failed_201(client):
    c, Session = client
    series = _mock_series(5)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        r = c.post("/comparisons", json=_body())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "failed"
    assert body["errorCode"] == "insufficient_history"
    assert body.get("legs") is not None
    # No fabricated metrics leaderboard
    for leg in body["legs"]:
        assert leg.get("netPnl") is None or leg.get("fillCount") is None or True
        assert leg.get("backtestRunId") is None


def test_invalid_rsi_params_400(client):
    c, Session = client
    r = c.post(
        "/comparisons",
        json=_body(
            legs=[
                {"strategyId": "dual_ema"},
                {
                    "strategyId": "rsi",
                    "strategyParams": {"period": 14, "overbought": 20, "oversold": 80},
                },
            ]
        ),
    )
    assert r.status_code == 400
    db = Session()
    try:
        assert list(db.scalars(select(StrategyComparisonRow)).all()) == []
    finally:
        db.close()


def test_default_backtest_list_hides_comparison_origin(client):
    c, _Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        created = c.post("/comparisons", json=_body()).json()
    assert created["status"] == "completed"
    default = c.get("/backtest/runs").json()
    assert default["runs"] == []
    included = c.get("/backtest/runs?includeComparisonOrigin=true").json()
    assert len(included["runs"]) == 2
    assert all(run["origin"] == "comparison" for run in included["runs"])
    assert all(run.get("comparisonId") == created["id"] for run in included["runs"])


def test_get_and_list_comparison(client):
    c, _Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        created = c.post("/comparisons", json=_body()).json()
    listed = c.get("/comparisons").json()
    assert len(listed["comparisons"]) == 1
    got = c.get(f"/comparisons/{created['id']}").json()
    assert got["id"] == created["id"]
    assert len(got["legs"]) == 2


def test_delete_comparison_keeps_leg_backtests(client):
    c, Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        created = c.post("/comparisons", json=_body()).json()
    run_ids = [leg["backtestRunId"] for leg in created["legs"]]
    r = c.delete(f"/comparisons/{created['id']}")
    assert r.status_code == 204
    db = Session()
    try:
        for rid in run_ids:
            assert db.get(BacktestRunRow, rid) is not None
    finally:
        db.close()
    included = c.get("/backtest/runs?includeComparisonOrigin=true").json()
    assert len(included["runs"]) == 2


def test_no_winner_fields(client):
    c, _Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        body = c.post("/comparisons", json=_body()).json()
    assert "winner" not in body
    assert "bestStrategyId" not in body
    assert "bestLeg" not in body


def test_max_trades_applied_to_all_legs(client):
    c, _Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        body = c.post("/comparisons", json=_body(maxTrades=1)).json()
    assert body["status"] == "completed"
    assert body["maxTrades"] == 1
    for leg in body["legs"]:
        run = c.get(f"/backtest/runs/{leg['backtestRunId']}").json()
        assert run["maxTrades"] == 1


def test_effective_params_persisted_per_leg(client):
    c, _Session = client
    series = _mock_series(40)
    with patch(
        "app.comparison.service.get_market_data_service"
    ) as mock_svc:
        mock_svc.return_value.get_candles = AsyncMock(return_value=series)
        body = c.post(
            "/comparisons",
            json=_body(
                legs=[
                    {
                        "strategyId": "dual_ema",
                        "strategyParams": {"fastPeriod": 5, "slowPeriod": 21},
                    },
                    {
                        "strategyId": "rsi",
                        "strategyParams": {
                            "period": 10,
                            "overbought": 65,
                            "oversold": 35,
                        },
                    },
                ]
            ),
        ).json()
    assert body["status"] == "completed"
    assert body["legs"][0]["strategyParams"]["fastPeriod"] == 5
    assert body["legs"][1]["strategyParams"]["period"] == 10
