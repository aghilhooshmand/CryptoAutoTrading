"""Feature 014 polish: Real path closed; Portfolio isolation; hard-stop authority."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import create_session, stop_session_async
from app.simulation.state_machine import SessionState, allows_strategy_execution


def test_014_simulation_modules_do_not_import_xt_account():
    root = Path(__file__).resolve().parents[2] / "app" / "simulation"
    # Feature 015 Real credential gates live in these modules; Simulation
    # pipeline/control must still stay XT-account-free.
    real_boundary = {"real_gates.py", "recovery.py", "session_service.py"}
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.name in real_boundary:
            continue
        text = path.read_text(encoding="utf-8")
        if "xt_account" in text or "XtPrivateClient" in text:
            offenders.append(str(path.relative_to(root.parent.parent)))
    assert offenders == []


@pytest.mark.skip(reason="Superseded by Feature 015 Controlled Real execution")
def test_real_execution_still_unavailable():
    from app.execution.port import ExecutionIntent
    from app.execution.real import REAL_EXECUTION_UNAVAILABLE, RealExecutionAdapter

    res = RealExecutionAdapter().execute(
        ExecutionIntent(
            side="BUY",
            symbol="btc_usdt",
            reference_price=Decimal("100"),
            fee_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.0005"),
            cash=Decimal("1000"),
            allocated_capital=Decimal("1000"),
            max_position_size=Decimal("1000"),
            position_side="flat",
            position_qty=Decimal("0"),
        )
    )
    assert res.ok is False
    assert res.reason_code == REAL_EXECUTION_UNAVAILABLE


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/hs.db", connect_args={"check_same_thread": False})
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
        "targetNetProfitRate": "0.01",
        "maxSessionLossRate": "0.01",
        "maxTrades": 20,
        "durationSeconds": 60,
        "strategyId": "dual_ema",
    }
    body.update(overrides)
    return body


def test_allows_strategy_only_when_running():
    assert allows_strategy_execution(SessionState.RUNNING)
    assert not allows_strategy_execution(SessionState.RECOVERY_BLOCKED)
    assert not allows_strategy_execution(SessionState.STOPPED)
    assert not allows_strategy_execution(SessionState.STOPPING)


def test_emergency_stop_prevents_further_strategy_ticks(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    db.commit()

    mock = AsyncMock()
    mock.get_quote = AsyncMock(
        return_value=MarketQuote(
            symbol="btc_usdt",
            lastPrice="100",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )
    )

    async def _stop():
        with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
            await stop_session_async(db, row.id, "emergency", clock=FakeClock(now))

    asyncio.run(_stop())
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "emergency"
    assert not allows_strategy_execution(SessionState(row.state))

    # Pipeline must no-op when not RUNNING
    async def _tick():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            await process_session_tick(db, row, FakeClock(now))

    fills_before = row.strategy_fill_count
    asyncio.run(_tick())
    db.refresh(row)
    assert row.strategy_fill_count == fills_before
    assert row.state == "STOPPED"


def test_duration_hard_stop_still_stops_session(db):
    row = create_session(db, _body(durationSeconds=60))
    started = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    later = datetime(2026, 8, 16, 12, 2, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = started
    db.commit()

    mock = AsyncMock()
    mock.get_quote = AsyncMock(
        return_value=MarketQuote(
            symbol="btc_usdt",
            lastPrice="100",
            source="XT",
            observedAt=later,
            retrievedAt=later,
            status=MarketStatus.FRESH,
        )
    )

    async def _tick():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
                await process_session_tick(db, row, FakeClock(later))

    asyncio.run(_tick())
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "duration_elapsed"


def test_max_loss_hard_stop_still_stops_session(db):
    row = create_session(db, _body(maxSessionLossRate="0.01"))
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row.state = "RUNNING"
    row.started_at = now
    row.cash = "1"
    row.position_side = "flat"
    row.position_qty = "0"
    # max_session_loss_amount is derived at create from allocated * rate
    db.commit()

    mock = AsyncMock()
    mock.get_quote = AsyncMock(
        return_value=MarketQuote(
            symbol="btc_usdt",
            lastPrice="100",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )
    )
    mock.get_candles = AsyncMock(side_effect=AssertionError("should stop before candles"))

    async def _tick():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            await process_session_tick(db, row, FakeClock(now))

    asyncio.run(_tick())
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "max_loss"
