"""Unit tests for Feature 008 Settings service."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, OperatorDefaultsRow
from app.settings import service as svc
from app.settings.starters import SINGLETON_ID, product_starter_defaults
from app.strategy.serialize import dumps_params


def _xt_override(body: dict, **overrides) -> dict:
    out = dict(body)
    for key in ("venue", "baseAsset", "quoteAsset", "canonicalSymbol", "venueProductId"):
        out.pop(key, None)
    out.update(overrides)
    return out


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/s.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()


def test_starters_shape():
    body = product_starter_defaults()
    assert body["symbol"] == "BTC/EUR"
    assert body["venue"] == "kraken"
    assert body["timeframe"] == "1h"
    assert body["startingCapital"] == "1000"
    assert body["allocatedCapital"] == "1000"
    assert body["maxPositionSize"] == "1000"
    assert body["targetNetProfitRate"] is None
    assert body["maxSessionLossRate"] is None
    assert body["maxTrades"] is None
    assert body["strategyId"] == "dual_ema"
    assert body["strategyParams"]["fastPeriod"] == 9


def test_get_empty_returns_starters(db):
    data = svc.get_settings(db)
    assert data["source"] == "starters"
    assert data["warning"] is None
    assert data["startingCapital"] == "1000"


def test_put_and_get_round_trip(db):
    body = _xt_override(
        product_starter_defaults(),
        symbol="eth_usdt",
        startingCapital="2000",
        allocatedCapital="1500",
        maxPositionSize="1000",
    )
    saved = svc.put_settings(db, body)
    assert saved["source"] == "saved"
    assert saved["symbol"] == "eth_usdt"
    assert saved["updatedAt"]

    again = svc.get_settings(db)
    assert again["source"] == "saved"
    assert again["symbol"] == "eth_usdt"
    assert again["startingCapital"] == "2000"


def test_invalid_nesting_leaves_prior(db):
    good = _xt_override(product_starter_defaults(), symbol="eth_usdt")
    svc.put_settings(db, good)

    bad = dict(good)
    bad["maxPositionSize"] = "5000"
    with pytest.raises(svc.SettingsError) as exc:
        svc.put_settings(db, bad)
    assert exc.value.code == "invalid_config"

    again = svc.get_settings(db)
    assert again["symbol"] == "eth_usdt"
    assert again["maxPositionSize"] == "1000"


def test_corrupt_row_fail_closed(db):
    db.add(
        OperatorDefaultsRow(
            id=SINGLETON_ID,
            symbol="btc_usdt",
            timeframe="1h",
            starting_capital="1000",
            allocated_capital="1000",
            max_position_size="1000",
            fee_rate="0.002",
            slippage_rate="0.0005",
            target_net_profit_rate=None,
            max_session_loss_rate=None,
            max_trades=None,
            strategy_id="not_a_real_strategy",
            strategy_params=dumps_params({}),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    data = svc.get_settings(db)
    assert data["source"] == "starters"
    assert data["warning"]
    assert data["strategyId"] == "dual_ema"


def test_save_does_not_call_trading_services(db, monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        "app.simulation.session_service.create_session",
        lambda *a, **k: calls.append("create_session") or MagicMock(),
    )
    monkeypatch.setattr(
        "app.backtest.service.create_and_run",
        lambda *a, **k: calls.append("backtest") or MagicMock(),
    )
    monkeypatch.setattr(
        "app.comparison.service.create_and_run",
        lambda *a, **k: calls.append("comparison") or MagicMock(),
    )

    svc.put_settings(db, product_starter_defaults())
    svc.reset_settings(db)
    assert calls == []


def test_saved_xt_settings_not_rewritten_on_get(db):
    xt_body = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "feeRate": "0.002",
        "slippageRate": "0.0005",
        "strategyId": "dual_ema",
        "strategyParams": {"fastPeriod": 9, "slowPeriod": 21},
    }
    saved = svc.put_settings(db, xt_body)
    assert saved["venue"] == "xt"
    assert saved["symbol"] == "btc_usdt"
    again = svc.get_settings(db)
    assert again["source"] == "saved"
    assert again["venue"] == "xt"
    assert again["symbol"] == "btc_usdt"
    assert again["canonicalSymbol"] == "BTC/USDT"

