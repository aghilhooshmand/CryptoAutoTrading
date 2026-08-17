"""Session reconciliation gates (Feature 014 FR-006)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import DecisionJournalRow, SimulationSessionRow, TradeJournalRow
from app.portfolio import identity
from app.portfolio import repository as portfolio_repo
from app.simulation.money import d
from app.simulation.portfolio_risk import base_asset_from_symbol

logger = logging.getLogger(__name__)

GATE_SESSION_JOURNAL = "reconcile_session_journal_mismatch"
GATE_WATERMARK = "reconcile_watermark_inconsistent"
GATE_PORTFOLIO = "reconcile_portfolio_mismatch"
GATE_UNSAFE_UNFLATTENED = "reconcile_unsafe_unflattened"
GATE_MARK = "reconcile_mark_untrustworthy"
GATE_GAP = "recovery_gap_unresolvable"
GATE_REAL_UNSETTLED = "xt_reconcile_unsettled"
GATE_REAL_PENDING = "resume_unavailable"
GATE_REAL_PARTIAL = "partial_filled_blocked"


_BLOCKING_REAL_RECONCILE = frozenset(
    {"unsettled", "partial_filled_blocked", "submit_failed"}
)


@dataclass
class ReconcileResult:
    passed: bool
    failed_gates: list[str] = field(default_factory=list)
    session_id: str = ""
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _replay_position_from_trades(trades: list[TradeJournalRow]) -> tuple[str, Decimal]:
    """Walk trades chronologically; return (side, qty)."""
    side = "flat"
    qty = Decimal("0")
    for t in trades:
        if t.side.upper() == "BUY":
            side = "long"
            qty = d(t.qty)
        elif t.side.upper() == "SELL":
            side = "flat"
            qty = Decimal("0")
    return side, qty


def _gate_session_journal(db: Session, row: SimulationSessionRow) -> bool:
    trades = (
        db.query(TradeJournalRow)
        .filter(TradeJournalRow.session_id == row.id)
        .order_by(TradeJournalRow.created_at.asc(), TradeJournalRow.id.asc())
        .all()
    )
    # Initial cash is starting_capital (create_session sets cash from starting).
    expected_cash = d(row.starting_capital)
    for t in trades:
        expected_cash += d(t.cash_delta)
    if expected_cash != d(row.cash):
        return False

    if not trades:
        return row.position_side == "flat" and d(row.position_qty) == Decimal("0")

    expected_side, expected_qty = _replay_position_from_trades(trades)
    if expected_side != row.position_side:
        return False
    if expected_side == "flat":
        return d(row.position_qty) == Decimal("0")
    return expected_qty == d(row.position_qty)


def _gate_watermark(db: Session, row: SimulationSessionRow) -> bool:
    trade_times = [
        t.candle_open_time
        for t in db.query(TradeJournalRow)
        .filter(
            TradeJournalRow.session_id == row.id,
            TradeJournalRow.candle_open_time.isnot(None),
        )
        .all()
    ]
    decision_times = [
        drow.candle_open_time
        for drow in db.query(DecisionJournalRow)
        .filter(
            DecisionJournalRow.session_id == row.id,
            DecisionJournalRow.candle_open_time.isnot(None),
        )
        .all()
    ]
    journal_times = [t for t in trade_times + decision_times if t is not None]
    if not journal_times:
        return True
    if row.last_processed_candle_open_time is None:
        return False
    return row.last_processed_candle_open_time >= max(journal_times)


def _gate_portfolio(db: Session, row: SimulationSessionRow) -> bool:
    base = base_asset_from_symbol(row.symbol)
    if row.allocation_id:
        usdt = portfolio_repo.get_holding(db, identity.QUOTE_ASSET)
        usdt_qty = d(usdt.quantity) if usdt is not None else Decimal("0")
        if usdt_qty != d(row.cash):
            return False
        base_h = portfolio_repo.get_holding(db, base)
        if row.position_side == "long":
            if base_h is None:
                return False
            return d(base_h.quantity) == d(row.position_qty)
        # flat: no base holding or zero qty
        if base_h is None:
            return True
        return d(base_h.quantity) == Decimal("0")

    # Unbound: long is unsafe to auto-resume (cannot verify Portfolio binding).
    if row.position_side == "long":
        return False
    # Unbound flat: fail if Portfolio still shows a non-zero base holding (projection conflict).
    base_h = portfolio_repo.get_holding(db, base)
    if base_h is not None and d(base_h.quantity) != Decimal("0"):
        return False
    return True


def _gate_unsafe_unflattened(row: SimulationSessionRow) -> bool:
    return row.position_flatten_status != "unsafe_unflattened"


def _gate_mark(row: SimulationSessionRow, mark_safe: bool | None) -> bool:
    if row.position_side != "long":
        return True
    if mark_safe is None:
        return False
    return bool(mark_safe)


def reconcile_session(
    db: Session,
    row: SimulationSessionRow,
    *,
    mark_safe: bool | None = None,
) -> ReconcileResult:
    """Run FR-006 gates G1–G5. Fail-closed; never invents corrections."""
    checked_at = datetime.now(timezone.utc)
    failed: list[str] = []

    if not _gate_session_journal(db, row):
        failed.append(GATE_SESSION_JOURNAL)
    if not _gate_watermark(db, row):
        failed.append(GATE_WATERMARK)
    if not _gate_portfolio(db, row):
        failed.append(GATE_PORTFOLIO)
    if not _gate_unsafe_unflattened(row):
        failed.append(GATE_UNSAFE_UNFLATTENED)
    if not _gate_mark(row, mark_safe):
        failed.append(GATE_MARK)

    passed = len(failed) == 0
    logger.info(
        "reconcile_session session_id=%s passed=%s failed_gates=%s",
        row.id,
        passed,
        failed,
    )
    return ReconcileResult(
        passed=passed,
        failed_gates=failed,
        session_id=row.id,
        checked_at=checked_at,
    )


def reconcile_real_session(
    db: Session,
    row: SimulationSessionRow,
    *,
    mark_safe: bool | None = None,
) -> ReconcileResult:
    """Real resume gates: local journals + XT settle; never uses Sim Portfolio."""
    from app.simulation.pending_confirmation import get_active_pending

    checked_at = datetime.now(timezone.utc)
    failed: list[str] = []

    if not _gate_session_journal(db, row):
        failed.append(GATE_SESSION_JOURNAL)
    if not _gate_watermark(db, row):
        failed.append(GATE_WATERMARK)
    if not _gate_unsafe_unflattened(row):
        failed.append(GATE_UNSAFE_UNFLATTENED)
    if not _gate_mark(row, mark_safe):
        failed.append(GATE_MARK)
    if get_active_pending(db, row.id) is not None:
        failed.append(GATE_REAL_PENDING)
    status = (row.real_reconcile_status or "").strip()
    if status in _BLOCKING_REAL_RECONCILE:
        failed.append(GATE_REAL_PARTIAL if status == "partial_filled_blocked" else GATE_REAL_UNSETTLED)

    passed = len(failed) == 0
    logger.info(
        "reconcile_real_session session_id=%s passed=%s failed_gates=%s",
        row.id,
        passed,
        failed,
    )
    return ReconcileResult(
        passed=passed,
        failed_gates=failed,
        session_id=row.id,
        checked_at=checked_at,
    )
