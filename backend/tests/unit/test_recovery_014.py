"""Feature 014 recover-and-reconcile tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow
from app.market_data.models import MarketQuote, MarketStatus
from app.simulation.recovery import recover_orphan_sessions
from app.simulation.state_machine import SessionState, allows_strategy_execution


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _row(**over) -> SimulationSessionRow:
    now = datetime.now(timezone.utc)
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


def test_recovery_pass_resumes_running():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(state="RUNNING")
    db.add(row)
    db.commit()

    async def _quote(symbol: str) -> MarketQuote:
        t = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000",
            source="XT",
            observedAt=t,
            retrievedAt=t,
            status=MarketStatus.FRESH,
        )

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=_quote)
    with patch("app.simulation.recovery.get_market_data_service", return_value=mock_svc):
        with patch(
            "app.simulation.recovery.apply_offline_gap_skip",
            new=AsyncMock(return_value=(True, None)),
        ):
            n = recover_orphan_sessions(db, now=now)
    assert n == 1
    db.refresh(row)
    assert row.state == "RUNNING"
    assert row.recovery_reason is None


def test_recovery_fail_blocks():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(cash="999", state="RUNNING")
    db.add(row)
    db.commit()

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=RuntimeError("x"))
    with patch("app.simulation.recovery.get_market_data_service", return_value=mock_svc):
        n = recover_orphan_sessions(db, now=now)
    assert n == 1
    db.refresh(row)
    assert row.state == SessionState.RECOVERY_BLOCKED.value
    assert row.recovery_reason is not None
    assert not allows_strategy_execution(SessionState(row.state))


def test_recovery_gap_fail_blocks():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(state="STOPPING")
    db.add(row)
    db.commit()

    async def _quote(symbol: str) -> MarketQuote:
        t = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000",
            source="XT",
            observedAt=t,
            retrievedAt=t,
            status=MarketStatus.FRESH,
        )

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=_quote)
    with patch("app.simulation.recovery.get_market_data_service", return_value=mock_svc):
        with patch(
            "app.simulation.recovery.apply_offline_gap_skip",
            new=AsyncMock(return_value=(False, "recovery_gap_unresolvable")),
        ):
            n = recover_orphan_sessions(db, now=now)
    assert n == 1
    db.refresh(row)
    assert row.state == "RECOVERY_BLOCKED"
    assert row.recovery_reason == "recovery_gap_unresolvable"


def test_blocked_does_not_allow_strategy():
    assert not allows_strategy_execution(SessionState.RECOVERY_BLOCKED)
