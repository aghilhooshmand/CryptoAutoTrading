"""Real blocked recovery — never auto-resume (Feature 015 FR-011)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow
from app.execution.real import set_client_factory_override
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.pending_confirmation import create_pending, get_active_pending
from app.simulation.real_gates import set_try_free_usdt_override
from app.simulation.recovery import recover_orphan_sessions
from app.simulation.session_service import (
    SessionError,
    create_session,
    resume_session_async,
    stop_session_async,
)
from app.simulation.state_machine import SessionState, allows_strategy_execution


def _db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/r.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    return TestingSession()


def _sim_row(**over) -> SimulationSessionRow:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="1000",
        max_position_size="1000",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.01",
        target_net_profit_amount="10",
        max_session_loss_amount="10",
        max_trades=10,
        duration_seconds=3600,
        fee_rate="0.001",
        slippage_rate="0.0005",
        cash="1000",
        position_side="flat",
        position_qty="0",
        position_flatten_status="n/a",
        created_at=now,
        updated_at=now,
    )
    base.update(over)
    return SimulationSessionRow(**base)


def _real_row(**over) -> SimulationSessionRow:
    return _sim_row(
        id="22222222-2222-2222-2222-222222222222",
        mode="real",
        starting_capital="25",
        allocated_capital="25",
        max_position_size="25",
        cash="25",
        **over,
    )


def _fresh_quote_svc():
    async def _quote(symbol: str) -> MarketQuote:
        t = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000",
            source="XT",
            observedAt=t,
            retrievedAt=t,
            status=MarketStatus.FRESH,
        )

    mock = AsyncMock()
    mock.get_quote = AsyncMock(side_effect=_quote)
    return mock


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    set_try_free_usdt_override(lambda: Decimal("100"))
    s = _db(tmp_path)
    try:
        yield s
    finally:
        s.close()
        set_try_free_usdt_override(None)
        set_client_factory_override(None)


def test_real_orphan_always_blocks_and_never_auto_resumes(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    real = _real_row(state="RUNNING")
    sim = _sim_row(state="RUNNING")
    db.add(real)
    db.add(sim)
    db.commit()
    with patch("app.simulation.recovery.get_market_data_service", return_value=_fresh_quote_svc()):
        with patch(
            "app.simulation.recovery.apply_offline_gap_skip",
            new=AsyncMock(return_value=(True, None)),
        ):
            n = recover_orphan_sessions(db, now=now)
    assert n == 2
    db.refresh(real)
    db.refresh(sim)
    assert real.state == SessionState.RECOVERY_BLOCKED.value
    assert real.recovery_reason == "real_restart_blocked"
    assert not allows_strategy_execution(SessionState(real.state))
    assert sim.state == "RUNNING"
    assert sim.recovery_reason is None


def test_real_recovery_discards_pending(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(
        db,
        {
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
        },
    )
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
    assert get_active_pending(db, row.id) is not None
    recover_orphan_sessions(db, now=now)
    db.refresh(row)
    assert row.state == "RECOVERY_BLOCKED"
    assert get_active_pending(db, row.id) is None


def test_unsettled_blocks_strategy_and_resume(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = _real_row(
        state="RECOVERY_BLOCKED",
        xt_order_id="xt-keep",
        real_reconcile_status="unsettled",
        recovery_reason="xt_reconcile_unsettled",
    )
    db.add(row)
    db.commit()
    assert not allows_strategy_execution(SessionState(row.state))

    async def _resume():
        with patch("app.simulation.recovery.get_market_data_service", return_value=_fresh_quote_svc()):
            with patch(
                "app.simulation.recovery.apply_offline_gap_skip",
                new=AsyncMock(return_value=(True, None)),
            ):
                return await resume_session_async(db, row.id, clock=FakeClock(now))

    with pytest.raises(SessionError) as exc:
        asyncio.run(_resume())
    assert exc.value.code == "resume_unavailable"
    db.refresh(row)
    assert row.state == "RECOVERY_BLOCKED"
    assert row.xt_order_id == "xt-keep"


def test_real_resume_succeeds_after_safe_reconcile(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = _real_row(
        state="RECOVERY_BLOCKED",
        recovery_reason="real_restart_blocked",
        real_reconcile_status="filled",
    )
    db.add(row)
    db.commit()

    async def _resume():
        with patch("app.simulation.recovery.get_market_data_service", return_value=_fresh_quote_svc()):
            with patch(
                "app.simulation.recovery.apply_offline_gap_skip",
                new=AsyncMock(return_value=(True, None)),
            ):
                return await resume_session_async(db, row.id, clock=FakeClock(now))

    updated = asyncio.run(_resume())
    assert updated.state == "RUNNING"
    assert updated.recovery_reason is None


def test_stop_from_real_blocked_skips_confirm(db):
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = _real_row(state="RECOVERY_BLOCKED", recovery_reason="real_restart_blocked")
    db.add(row)
    db.commit()
    mock = _fresh_quote_svc()

    async def _stop():
        with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
            return await stop_session_async(db, row.id, "manual", clock=FakeClock(now))

    stopped = asyncio.run(_stop())
    assert stopped.state == "STOPPED"
    assert get_active_pending(db, row.id) is None
