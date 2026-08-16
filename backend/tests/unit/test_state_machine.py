"""State machine and recovery tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow
from app.simulation.recovery import recover_orphan_sessions
from app.simulation.state_machine import (
    SessionState,
    allows_strategy_execution,
    can_transition,
    is_active,
    recover_to_blocked,
    transition,
)


def test_legal_transitions():
    assert can_transition(SessionState.CONFIGURED, SessionState.RUNNING)
    assert transition(SessionState.RUNNING, SessionState.STOPPING) == SessionState.STOPPING
    assert can_transition(SessionState.RUNNING, SessionState.RECOVERY_BLOCKED)
    assert can_transition(SessionState.STOPPING, SessionState.RECOVERY_BLOCKED)
    assert can_transition(SessionState.RECOVERY_BLOCKED, SessionState.RUNNING)
    assert can_transition(SessionState.RECOVERY_BLOCKED, SessionState.STOPPING)
    assert can_transition(SessionState.STOPPING, SessionState.RUNNING)


def test_illegal_transition():
    try:
        transition(SessionState.STOPPED, SessionState.RUNNING)
        assert False
    except ValueError:
        pass
    try:
        transition(SessionState.STOPPED, SessionState.RECOVERY_BLOCKED)
        assert False
    except ValueError:
        pass


def test_recover_to_blocked_helper():
    assert recover_to_blocked(SessionState.RUNNING) == SessionState.RECOVERY_BLOCKED
    assert recover_to_blocked(SessionState.STOPPING) == SessionState.RECOVERY_BLOCKED


def test_strategy_execution_only_running():
    assert allows_strategy_execution(SessionState.RUNNING)
    assert not allows_strategy_execution(SessionState.RECOVERY_BLOCKED)
    assert not allows_strategy_execution(SessionState.STOPPING)
    assert not allows_strategy_execution(SessionState.STOPPED)
    assert is_active(SessionState.RECOVERY_BLOCKED)
    assert is_active(SessionState.RUNNING)
    assert is_active(SessionState.STOPPING)
    assert not is_active(SessionState.STOPPED)


def test_recovery_marks_stopped():
    """Long orphan without trustworthy mark → RECOVERY_BLOCKED (G5), not STOPPED."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime.now(timezone.utc)
    row = SimulationSessionRow(
        id="11111111-1111-1111-1111-111111111111",
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="100",
        allocated_capital="100",
        max_position_size="100",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.01",
        target_net_profit_amount="1",
        max_session_loss_amount="1",
        max_trades=5,
        duration_seconds=60,
        fee_rate="0.001",
        slippage_rate="0.0005",
        cash="50",
        position_side="long",
        position_qty="1",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()

    async def _fail_quote(symbol: str):
        raise RuntimeError("unavailable")

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=_fail_quote)
    with patch("app.simulation.recovery.get_market_data_service", return_value=mock_svc):
        n = recover_orphan_sessions(db, now=now)
    assert n == 1
    db.refresh(row)
    assert row.state == "RECOVERY_BLOCKED"
    assert row.recovery_reason in (
        "reconcile_mark_untrustworthy",
        "reconcile_session_journal_mismatch",
        "reconcile_portfolio_mismatch",
    )
