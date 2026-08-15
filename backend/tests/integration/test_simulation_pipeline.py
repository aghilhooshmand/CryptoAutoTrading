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
    from app.portfolio import service as portfolio_svc

    portfolio_svc.set_funding(s, "100000")
    try:
        yield s
    finally:
        s.close()


def _session_body(**overrides):
    body = {
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
    }
    body.update(overrides)
    return body


def _flat_market(now: datetime):
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
    return mock, candles[-1].openTime


def _run_tick(db, row, mock, now):
    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            await process_session_tick(db, row, clock)

    asyncio.run(_run())


def test_pipeline_important_only_skips_hold_but_advances_cursor(db):
    row = create_session(db, _session_body())
    assert row.decision_log_mode == "important_only"
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    mock, newest_open = _flat_market(now)
    _run_tick(db, row, mock, now)

    db.refresh(row)
    assert row.last_processed_candle_open_time == newest_open
    decisions = db.query(DecisionJournalRow).filter_by(session_id=row.id).all()
    assert decisions == []
    assert row.cash == "500"
    assert row.trade_count == 0
    assert Decimal(row.position_qty) == 0


def test_pipeline_full_audit_persists_hold(db):
    row = create_session(db, _session_body(decisionLogMode="full_audit"))
    assert row.decision_log_mode == "full_audit"
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    mock, newest_open = _flat_market(now)
    _run_tick(db, row, mock, now)

    db.refresh(row)
    assert row.last_processed_candle_open_time == newest_open
    decisions = db.query(DecisionJournalRow).filter_by(session_id=row.id).all()
    assert len(decisions) == 1
    assert decisions[0].signal == "HOLD"


def test_pipeline_legacy_null_mode_persists_hold(db):
    row = create_session(db, _session_body(decisionLogMode="important_only"))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    row.decision_log_mode = None  # legacy rows
    db.commit()

    mock, newest_open = _flat_market(now)
    _run_tick(db, row, mock, now)

    db.refresh(row)
    assert row.last_processed_candle_open_time == newest_open
    decisions = db.query(DecisionJournalRow).filter_by(session_id=row.id).all()
    assert len(decisions) == 1
    assert decisions[0].signal == "HOLD"


def test_pipeline_important_only_still_persists_risk_reject(db):
    from app.simulation.control.risk import RiskDecision
    from app.strategy.base import SignalSide, StrategySignal

    row = create_session(db, _session_body(decisionLogMode="important_only"))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    mock, newest_open = _flat_market(now)
    buy = StrategySignal(
        side=SignalSide.BUY,
        candle_open_time=newest_open,
        fast_ema=Decimal("101"),
        slow_ema=Decimal("100"),
        reason_code="cross_up",
    )
    reject = RiskDecision(
        approved=False,
        reason_code="maximum_trades_reached",
        reason_message="max trades",
        trigger_stop=None,
    )

    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            with patch("app.simulation.pipeline.build_from_stored") as build:
                strat = build.return_value
                strat.evaluate.return_value = buy
                strat.min_history_candles.return_value = 1
                with patch("app.simulation.pipeline.RiskManager.review", return_value=reject):
                    await process_session_tick(db, row, clock)

    asyncio.run(_run())

    db.refresh(row)
    assert row.last_processed_candle_open_time == newest_open
    decisions = db.query(DecisionJournalRow).filter_by(session_id=row.id).all()
    assert len(decisions) == 1
    assert decisions[0].signal == "BUY"
    assert decisions[0].outcome == "rejected"
