"""Real BUY confirmation gate — pipeline must not place until confirm (Feature 015 US1)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DecisionJournalRow, PendingEntryConfirmationRow
from app.execution.real import set_client_factory_override
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pending_confirmation import create_pending, get_active_pending
from app.simulation.pipeline import process_session_tick
from app.simulation.real_gates import set_try_free_usdt_override
from app.simulation.session_service import create_session, decline_entry
from app.strategy.base import SignalSide, StrategySignal


class _AlwaysBuyStrategy:
    def min_history_candles(self) -> int:
        return 1

    def evaluate(self, closes):
        last = closes[-1]
        return StrategySignal(
            side=SignalSide.BUY,
            candle_open_time=last.open_time,
            fast_ema=None,
            slow_ema=None,
            reason_code="test_buy",
        )


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/g.db", connect_args={"check_same_thread": False})
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
        "durationSeconds": 86400,
        "strategyId": "dual_ema",
    }
    body.update(overrides)
    return body


def _market(now: datetime, *, mark: str = "65000"):
    base_ms = int(now.timestamp() * 1000) - 30 * 3600 * 1000
    candles = [
        Candlestick(
            openTime=base_ms + i * 3600 * 1000,
            open=mark,
            high=mark,
            low=mark,
            close=mark,
        )
        for i in range(30)
    ]
    series = CandlestickSeries(
        symbol="btc_usdt",
        interval="1h",
        candles=candles,
        source="XT",
        retrievedAt=now,
    )
    quote = MarketQuote(
        symbol="btc_usdt",
        lastPrice=mark,
        source="XT",
        observedAt=now,
        retrievedAt=now,
        status=MarketStatus.FRESH,
    )
    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=quote)
    mock.get_candles = AsyncMock(return_value=series)
    return mock


def _run_tick(db, row, mock, now):
    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysBuyStrategy()):
                await process_session_tick(db, row, clock)

    asyncio.run(_run())


def _start_running(db, row, now):
    clock = FakeClock(now)
    mock = _market(now)

    async def _start():
        with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
            from app.simulation.session_service import start_session_async

            return await start_session_async(db, row.id, clock=clock)

    return asyncio.run(_start())


def test_real_buy_creates_pending_without_xt_place(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row = _start_running(db, row, now)

    place_mock = MagicMock()
    set_client_factory_override(lambda _creds: place_mock)

    _run_tick(db, row, _market(now), now)

    pending = (
        db.query(PendingEntryConfirmationRow)
        .filter(PendingEntryConfirmationRow.session_id == row.id)
        .one()
    )
    assert pending.status == "pending"
    assert place_mock.place_market_order.call_count == 0

    decision = (
        db.query(DecisionJournalRow)
        .filter(DecisionJournalRow.session_id == row.id, DecisionJournalRow.outcome == "pending_confirmation")
        .one()
    )
    assert decision.reason_code == "awaiting_real_confirm"


def test_decline_entry_discards_pending_without_xt(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="25",
        reference_price="65000",
        now=now,
    )
    db.commit()

    place_mock = MagicMock()
    set_client_factory_override(lambda _creds: place_mock)

    declined = decline_entry(db, row.id, clock=FakeClock(now))
    assert declined.state == "RUNNING"
    assert get_active_pending(db, row.id) is None
    place_mock.place_market_order.assert_not_called()


def test_stop_discards_pending(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(db, _real_body())
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="25",
        reference_price="65000",
        now=now,
    )
    db.commit()

    async def _stop():
        from app.simulation.session_service import stop_session_async

        await stop_session_async(db, row.id, "manual", clock=FakeClock(now))

    asyncio.run(_stop())

    pending_rows = (
        db.query(PendingEntryConfirmationRow)
        .filter(PendingEntryConfirmationRow.session_id == row.id)
        .all()
    )
    assert len(pending_rows) == 1
    assert pending_rows[0].status == "cancelled"
