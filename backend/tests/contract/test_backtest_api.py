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
        "strategyId": "dual_ema",
    }
    base.update(over)
    return base


def test_omit_strategy_id_rejected(client):
    c, _Session = client
    body = _body()
    del body["strategyId"]
    r = c.post("/backtest/runs", json=body)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] in ("missing_strategy", "invalid_config")


def test_alias_persists_canonical(client):
    c, _Session = client
    from unittest.mock import AsyncMock, patch

    from app.market_data.models import CandleInterval, CandlestickSeries

    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(30))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post("/backtest/runs", json=_body(strategyId="dual_ema_9_21"))
    assert r.status_code == 201
    data = r.json()
    assert data["strategyId"] == "dual_ema"
    assert data["strategyParams"]["fastPeriod"] == 9
    assert data["strategyParams"]["slowPeriod"] == 21


def test_insufficient_history_uses_slow_period(client):
    c, _Session = client
    from unittest.mock import AsyncMock, patch

    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(40))
    # slow=50 → need ≥50 candles; 40 → insufficient
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post(
            "/backtest/runs",
            json=_body(
                strategyParams={"fastPeriod": 9, "slowPeriod": 50},
                endTime=1_700_000_000_000 + 60 * 3_600_000,
            ),
        )
    assert r.status_code == 201
    assert r.json()["status"] == "failed"
    assert r.json()["errorCode"] == "insufficient_history"


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


@pytest.mark.parametrize(
    ("strategy_id", "params", "expected_params"),
    [
        ("rsi", None, {"period": 14, "overbought": 70, "oversold": 30}),
        ("macd", None, {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}),
        ("bollinger_bands", {"period": 20, "stdDev": "2.5"}, {"period": 20, "stdDev": "2.5"}),
        ("breakout", None, {"lookback": 20}),
    ],
)
def test_create_accepts_new_strategies(client, strategy_id, params, expected_params):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(40))
    body = _body(strategyId=strategy_id)
    if params is not None:
        body["strategyParams"] = params
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post("/backtest/runs", json=body)
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
    c, _Session = client
    r = c.post(
        "/backtest/runs",
        json=_body(strategyId=strategy_id, strategyParams=params),
    )
    assert r.status_code == 400
    assert message_part in r.json()["detail"]["error"]["message"]


@pytest.mark.parametrize(
    ("strategy_id", "params", "candle_count"),
    [
        ("rsi", {"period": 14, "overbought": 70, "oversold": 30}, 13),
        ("macd", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, 34),
        ("bollinger_bands", {"period": 20, "stdDev": "2.0"}, 19),
        ("breakout", {"lookback": 20}, 19),
    ],
)
def test_insufficient_history_for_new_strategies(client, strategy_id, params, candle_count):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(candle_count))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post(
            "/backtest/runs",
            json=_body(strategyId=strategy_id, strategyParams=params),
        )
    assert r.status_code == 201
    assert r.json()["status"] == "failed"
    assert r.json()["errorCode"] == "insufficient_history"


def test_create_rejects_invalid_take_profit_percent(client):
    c, _Session = client
    r = c.post("/backtest/runs", json=_body(takeProfitPercent="0"))
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "invalid_config"


def test_create_persists_tpsl_percents(client):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(40))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post(
            "/backtest/runs",
            json=_body(takeProfitPercent="0.02", stopLossPercent="0.01"),
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["takeProfitPercent"] == "0.02"
    assert data["stopLossPercent"] == "0.01"


def test_legacy_xt_symbol_infers_identity(client):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(30))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post("/backtest/runs", json=_body())
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["venue"] == "xt"
    assert data["symbol"] == "btc_usdt"
    assert data["venueProductId"] == "btc_usdt"
    again = c.get(f"/backtest/runs/{data['id']}").json()
    assert again["canonicalSymbol"] == "BTC/USDT"


def test_kraken_identity_round_trip(client):
    c, _Session = client
    mock = AsyncMock()
    mock.get_candles = AsyncMock(return_value=_mock_series(30))
    with patch("app.backtest.service.get_market_data_service", return_value=mock):
        r = c.post(
            "/backtest/runs",
            json=_body(
                symbol="BTC/EUR",
                venue="kraken",
                baseAsset="BTC",
                quoteAsset="EUR",
                canonicalSymbol="BTC/EUR",
                venueProductId="XXBTZEUR",
            ),
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["venue"] == "kraken"
    assert data["canonicalSymbol"] == "BTC/EUR"
    assert data["venueProductId"] == "XXBTZEUR"
    assert mock.get_candles.await_args.args[0] == "XXBTZEUR"

