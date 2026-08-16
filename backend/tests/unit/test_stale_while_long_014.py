"""Feature 014 FR-011 stale-while-long pipeline tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.control.risk import UNSAFE_QUOTE_LIMIT
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import create_session


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/stale.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    from app.portfolio import service as portfolio_svc

    portfolio_svc.set_funding(s, "100000")
    try:
        yield s
    finally:
        s.close()


def _body(**overrides):
    body = {
        "mode": "simulation",
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startingCapital": "500",
        "allocatedCapital": "500",
        "maxPositionSize": "500",
        "targetNetProfitRate": "0.5",
        "maxSessionLossRate": "0.5",
        "maxTrades": 20,
        "durationSeconds": 86400,
        "strategyId": "dual_ema",
    }
    body.update(overrides)
    return body


def _unsafe_quote(now: datetime) -> MarketQuote:
    return MarketQuote(
        symbol="btc_usdt",
        lastPrice="100",
        source="XT",
        observedAt=now,
        retrievedAt=now,
        status=MarketStatus.STALE,
    )


def _run_tick(db, row, mock, now):
    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
                await process_session_tick(db, row, clock)

    asyncio.run(_run())


def test_unsafe_mark_while_long_increments_streak_and_blocks_entries(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    row.position_side = "long"
    row.position_qty = "0.01"
    row.cash = "0"
    row.unsafe_quote_streak = 0
    row.trade_count = 1
    row.strategy_fill_count = 1
    db.commit()

    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=_unsafe_quote(now))
    mock.get_candles = AsyncMock(side_effect=AssertionError("must not fetch candles on unsafe mark"))

    _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.state == "RUNNING"
    assert row.unsafe_quote_streak == 1
    assert row.strategy_fill_count == 1
    mock.get_candles.assert_not_called()


def test_unsafe_mark_streak_exhaustion_stops_without_invented_flatten(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    row.position_side = "long"
    row.position_qty = "0.01"
    row.cash = "0"
    row.unsafe_quote_streak = UNSAFE_QUOTE_LIMIT - 1
    row.trade_count = 1
    row.strategy_fill_count = 1
    db.commit()

    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=_unsafe_quote(now))

    _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "unrecoverable_unsafe_market_data"
    assert row.position_side == "long"
    assert Decimal(row.position_qty) == Decimal("0.01")
    assert row.position_flatten_status == "unsafe_unflattened"
