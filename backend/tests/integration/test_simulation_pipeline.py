"""Integration: pipeline tick with FakeClock and fake market data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DecisionJournalRow
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import create_session


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


def test_pipeline_hold_journals_without_fill(db):
    row = create_session(
        db,
        {
            "mode": "simulation",
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startingCapital": "500",
            "allocatedCapital": "500",
            "maxPositionSize": "500",
            "targetNetProfitRate": "0.01",
            "maxSessionLossRate": "0.007",
            "maxTrades": 20,
            "durationSeconds": 86400,
            "strategyId": "dual_ema",
        },
    )
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    candles = []
    base_ms = int(now.timestamp() * 1000) - 30 * 3600 * 1000
    for i in range(30):
        candles.append(
            Candlestick(
                openTime=base_ms + i * 3600 * 1000,
                open="100",
                high="100",
                low="100",
                close="100",
            )
        )
    series = CandlestickSeries(
        symbol="btc_usdt",
        interval="1h",
        candles=candles,
        source="XT",
        retrievedAt=now,
    )
    quote = MarketQuote(
        symbol="btc_usdt",
        lastPrice="100",
        source="XT",
        observedAt=now,
        retrievedAt=now,
        status=MarketStatus.FRESH,
    )
    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=quote)
    mock.get_candles = AsyncMock(return_value=series)

    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            await process_session_tick(db, row, clock)

    asyncio.run(_run())

    db.refresh(row)
    assert row.last_processed_candle_open_time is not None
    decisions = db.query(DecisionJournalRow).filter_by(session_id=row.id).all()
    assert len(decisions) == 1
    assert decisions[0].signal == "HOLD"
    assert row.cash == "500"
    assert row.trade_count == 0
    assert Decimal(row.position_qty) == 0
