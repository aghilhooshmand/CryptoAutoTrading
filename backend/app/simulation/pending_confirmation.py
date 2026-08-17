"""Pending Real BUY confirmation helpers (Feature 015)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import PendingEntryConfirmationRow

PENDING_TTL = timedelta(minutes=5)
STATUS_PENDING = "pending"
TERMINAL = frozenset({"confirmed", "declined", "expired", "cancelled", "rejected"})


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_active_pending(db: Session, session_id: str) -> PendingEntryConfirmationRow | None:
    return (
        db.query(PendingEntryConfirmationRow)
        .filter(
            PendingEntryConfirmationRow.session_id == session_id,
            PendingEntryConfirmationRow.status == STATUS_PENDING,
        )
        .order_by(PendingEntryConfirmationRow.created_at.desc())
        .first()
    )


def create_pending(
    db: Session,
    *,
    session_id: str,
    symbol: str,
    proposed_notional: Decimal | str,
    reference_price: Decimal | str,
    now: datetime | None = None,
    decision_journal_ref: str | None = None,
) -> PendingEntryConfirmationRow:
    existing = get_active_pending(db, session_id)
    if existing is not None:
        raise ValueError("pending_already_exists")
    created = _aware(now or datetime.now(timezone.utc))
    row = PendingEntryConfirmationRow(
        id=str(uuid.uuid4()),
        session_id=session_id,
        symbol=symbol,
        side="BUY",
        proposed_notional=str(proposed_notional),
        reference_price=str(reference_price),
        status=STATUS_PENDING,
        decision_journal_ref=decision_journal_ref,
        created_at=created,
        expires_at=created + PENDING_TTL,
    )
    db.add(row)
    db.flush()
    return row


def expire_if_due(
    db: Session,
    row: PendingEntryConfirmationRow,
    *,
    now: datetime | None = None,
) -> PendingEntryConfirmationRow:
    """If pending and past expires_at, mark expired. Does not reuse intent."""
    if row.status != STATUS_PENDING:
        return row
    current = _aware(now or datetime.now(timezone.utc))
    if current >= _aware(row.expires_at):
        row.status = "expired"
        db.flush()
    return row


def expire_due_for_session(
    db: Session,
    session_id: str,
    *,
    now: datetime | None = None,
) -> PendingEntryConfirmationRow | None:
    row = get_active_pending(db, session_id)
    if row is None:
        return None
    return expire_if_due(db, row, now=now)


def discard_pending(
    db: Session,
    row: PendingEntryConfirmationRow,
    *,
    status: str,
) -> PendingEntryConfirmationRow:
    if status not in TERMINAL:
        raise ValueError(f"invalid_terminal_status:{status}")
    if row.status != STATUS_PENDING:
        raise ValueError("pending_not_active")
    row.status = status
    db.flush()
    return row


def discard_all_pending_for_session(
    db: Session,
    session_id: str,
    *,
    status: str = "cancelled",
) -> int:
    rows = (
        db.query(PendingEntryConfirmationRow)
        .filter(
            PendingEntryConfirmationRow.session_id == session_id,
            PendingEntryConfirmationRow.status == STATUS_PENDING,
        )
        .all()
    )
    for row in rows:
        row.status = status
    if rows:
        db.flush()
    return len(rows)


def pending_to_dict(row: PendingEntryConfirmationRow | None) -> dict | None:
    if row is None or row.status != STATUS_PENDING:
        return None
    return {
        "id": row.id,
        "symbol": row.symbol,
        "side": row.side,
        "proposedNotional": row.proposed_notional,
        "referencePrice": row.reference_price,
        "status": row.status,
        "createdAt": row.created_at.isoformat().replace("+00:00", "Z"),
        "expiresAt": row.expires_at.isoformat().replace("+00:00", "Z"),
    }
