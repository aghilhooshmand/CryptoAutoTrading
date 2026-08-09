"""Startup recovery: never silently resume RUNNING sessions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.simulation.state_machine import SessionState


def recover_orphan_sessions(db: Session, now: datetime | None = None) -> int:
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
        count += 1
    if count:
        db.commit()
    return count
