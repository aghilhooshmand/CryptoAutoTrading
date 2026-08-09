"""State machine and recovery tests."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow
from app.simulation.recovery import recover_orphan_sessions
from app.simulation.state_machine import SessionState, can_transition, transition


def test_legal_transitions():
    assert can_transition(SessionState.CONFIGURED, SessionState.RUNNING)
    assert transition(SessionState.RUNNING, SessionState.STOPPING) == SessionState.STOPPING


def test_illegal_transition():
    try:
        transition(SessionState.STOPPED, SessionState.RUNNING)
        assert False
    except ValueError:
        pass


def test_recovery_marks_stopped():
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
    n = recover_orphan_sessions(db, now=now)
    assert n == 1
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "backend_restart"
    assert row.position_flatten_status == "unsafe_unflattened"
