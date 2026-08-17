"""Startup recover-and-reconcile (Feature 014)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.market_data.models import MarketStatus
from app.market_data.public_retry import PublicRetryExhausted, with_public_retry
from app.market_data.service import get_market_data_service
from app.simulation.control import reasons as risk_reasons
from app.simulation.gap_skip import apply_offline_gap_skip
from app.simulation.pending_confirmation import discard_all_pending_for_session
from app.simulation.reconcile import reconcile_session
from app.simulation.state_machine import SessionState, recover_to_blocked, transition

logger = logging.getLogger(__name__)


async def _mark_safe_for_row(row: SimulationSessionRow) -> bool:
    if row.position_side != "long":
        return True
    try:

        async def _call():
            return await get_market_data_service().get_quote(row.symbol)

        quote = await with_public_retry(_call)
    except (PublicRetryExhausted, Exception):  # noqa: BLE001
        return False
    return quote.status == MarketStatus.FRESH


def _enter_blocked(
    row: SimulationSessionRow,
    *,
    reason: str,
    detail: str | None,
    now: datetime,
) -> None:
    current = SessionState(row.state)
    if current != SessionState.RECOVERY_BLOCKED:
        recover_to_blocked(current)
    row.state = SessionState.RECOVERY_BLOCKED.value
    row.recovery_reason = reason
    row.recovery_detail = detail
    row.last_recovery_at = now
    row.updated_at = now


def _clear_recovery(row: SimulationSessionRow, now: datetime) -> None:
    row.recovery_reason = None
    row.recovery_detail = None
    row.last_recovery_at = now
    row.updated_at = now


async def recover_orphan_sessions_async(
    db: Session, now: datetime | None = None
) -> int:
    """Reconcile orphan RUNNING/STOPPING; resume only if G1–G5 + gap-skip pass."""
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(SimulationSessionRow)
        .filter(
            SimulationSessionRow.state.in_(
                [SessionState.RUNNING.value, SessionState.STOPPING.value]
            )
        )
        .all()
    )
    count = 0
    for row in rows:
        if row.mode == "real":
            discarded = discard_all_pending_for_session(db, row.id, status="cancelled")
            await _best_effort_refresh_xt_order(row)
            _enter_blocked(
                row,
                reason=risk_reasons.REAL_RESTART_BLOCKED,
                detail=risk_reasons.message_for(risk_reasons.REAL_RESTART_BLOCKED)
                + (f"; discarded {discarded} pending confirmation(s)" if discarded else ""),
                now=now,
            )
            logger.info(
                "real_restart_blocked session_id=%s xt_order_id=%s",
                row.id,
                row.xt_order_id,
            )
            count += 1
            continue

        mark_safe = await _mark_safe_for_row(row)
        result = reconcile_session(db, row, mark_safe=mark_safe)
        row.last_recovery_at = now

        if not result.passed:
            reason = result.failed_gates[0] if result.failed_gates else "reconcile_failed"
            detail = ",".join(result.failed_gates) if result.failed_gates else None
            _enter_blocked(row, reason=reason, detail=detail, now=now)
            logger.info(
                "recovery_blocked session_id=%s reason=%s gates=%s",
                row.id,
                reason,
                result.failed_gates,
            )
            count += 1
            continue

        ok, gap_err = await apply_offline_gap_skip(db, row)
        if not ok:
            _enter_blocked(
                row,
                reason=gap_err or "recovery_gap_unresolvable",
                detail=gap_err,
                now=now,
            )
            logger.info(
                "recovery_blocked session_id=%s reason=%s",
                row.id,
                gap_err,
            )
            count += 1
            continue

        # Gates + gap-skip passed → RUNNING (from RUNNING or STOPPING).
        current = SessionState(row.state)
        if current != SessionState.RUNNING:
            transition(current, SessionState.RUNNING)
        row.state = SessionState.RUNNING.value
        _clear_recovery(row, now)
        logger.info("recovery_resumed session_id=%s", row.id)
        count += 1

    if count:
        db.commit()
    return count


def recover_orphan_sessions(db: Session, now: datetime | None = None) -> int:
    """Sync wrapper for tests / callers without a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(recover_orphan_sessions_async(db, now=now))
    raise RuntimeError(
        "recover_orphan_sessions() cannot be called from a running event loop; "
        "use await recover_orphan_sessions_async(...)"
    )


async def _best_effort_refresh_xt_order(row: SimulationSessionRow) -> None:
    """Update reconcile_status from Feature 013 get_order; never auto-resumes."""
    if not row.xt_order_id:
        return
    try:
        from app.execution.real import _FILLED_STATES, _PARTIAL_STATES, _REJECTED_STATES, _client_for, _order_state
        from app.xt_account.credentials import load_credentials

        client = _client_for(load_credentials())
        try:
            raw = await client.get_order(row.xt_order_id)
        finally:
            await client.aclose()
        status, _executed, _price = _order_state(raw)
        if status in _FILLED_STATES:
            row.real_reconcile_status = "filled"
        elif status in _PARTIAL_STATES:
            row.real_reconcile_status = "partial_filled_blocked"
        elif status in _REJECTED_STATES:
            row.real_reconcile_status = "rejected"
    except Exception:  # noqa: BLE001
        logger.info(
            "real_xt_refresh_skipped session_id=%s order_id=%s",
            row.id,
            row.xt_order_id,
        )
