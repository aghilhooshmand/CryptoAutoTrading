"""Startup recovery: never silently resume RUNNING sessions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.simulation.final_result import SOURCE_RECOVERY, persist_final_result
from app.simulation.state_machine import SessionState


def recover_orphan_sessions(db: Session, now: datetime | None = None) -> int:
    """Fail-closed: orphan RUNNING/STOPPING → STOPPED + freeze. Never resume."""
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(SimulationSessionRow)
        .filter(SimulationSessionRow.state.in_([SessionState.RUNNING.value, SessionState.STOPPING.value]))
        .all()
    )
    count = 0
    for row in rows:
        if row.position_side == "long":
            row.position_flatten_status = "unsafe_unflattened"
        row.state = SessionState.STOPPED.value
        row.stop_reason = "backend_restart"
        row.stopped_at = now
        row.updated_at = now
        # No market mark on recovery — long remains incomplete freeze
        persist_final_result(
            db,
            row,
            source=SOURCE_RECOVERY,
            frozen_at=now,
            mark_price=None,
            mark_safe=False,
        )
        count += 1
    if count:
        db.commit()
    return count
