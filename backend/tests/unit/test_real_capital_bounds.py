"""Real capital/position bounds at create and confirm (Feature 015 US3)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.execution.real import set_client_factory_override
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pending_confirmation import create_pending
from app.simulation.real_gates import set_try_free_usdt_override
from app.simulation.session_service import confirm_entry_async, create_session, SessionError


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/b.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    set_try_free_usdt_override(lambda: Decimal("100"))
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()
        set_try_free_usdt_override(None)
        set_client_factory_override(None)


def _real_body(**overrides):
    body = {
        "mode": "real",
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "allocatedCapital": "25",
        "maxPositionSize": "25",
        "targetNetProfitRate": "0.01",
        "maxSessionLossRate": "0.007",
        "maxTrades": 20,
        "durationSeconds": 3600,
        "strategyId": "dual_ema",
    }
    body.update(overrides)
    return body


def _fresh_quote():
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    mock = AsyncMock()
    mock.get_quote = AsyncMock(
        return_value=MarketQuote(
            symbol="btc_usdt",
            lastPrice="65000",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )
    )
    return mock


def test_create_rejects_multi_symbol(db):
    with pytest.raises(SessionError) as exc:
        create_session(db, _real_body(symbol="btc_usdt,eth_usdt"))
    assert exc.value.code == "invalid_config"


def test_create_rejects_non_flat_start(db):
    with pytest.raises(SessionError) as exc:
        create_session(db, _real_body(positionSide="long"))
    assert exc.value.code == "invalid_config"


def test_confirm_rejects_when_not_flat(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row.state = "RUNNING"
    row.started_at = now
    row.position_side = "long"
    row.position_qty = "0.001"
    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="25",
        reference_price="65000",
        now=now,
    )
    db.commit()
    place = MagicMock()
    set_client_factory_override(lambda _c: place)
    with pytest.raises(SessionError) as exc:
        asyncio.run(confirm_entry_async(db, row.id, clock=FakeClock(now)))
    assert exc.value.code == "confirm_validation_failed"
    place.place_market_order.assert_not_called()


def test_confirm_rejects_cap_without_xt(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row.state = "RUNNING"
    row.started_at = now
    row.allocated_capital = "51"
    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="51",
        reference_price="65000",
        now=now,
    )
    db.commit()
    place = MagicMock()
    set_client_factory_override(lambda _c: place)
    with pytest.raises(SessionError) as exc:
        asyncio.run(confirm_entry_async(db, row.id, clock=FakeClock(now)))
    assert exc.value.code == "real_capital_cap_exceeded"
    place.place_market_order.assert_not_called()


def test_confirm_xt_free_below_notional_does_not_place(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row.state = "RUNNING"
    row.started_at = now
    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="25",
        reference_price="65000",
        now=now,
    )
    db.commit()
    place = MagicMock()
    set_client_factory_override(lambda _c: place)
    set_try_free_usdt_override(lambda: Decimal("1"))
    with patch("app.simulation.session_service.get_market_data_service", return_value=_fresh_quote()):
        with pytest.raises(SessionError) as exc:
            asyncio.run(confirm_entry_async(db, row.id, clock=FakeClock(now)))
    assert exc.value.code == "insufficient_xt_free"
    place.place_market_order.assert_not_called()
