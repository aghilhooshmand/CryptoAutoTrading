"""Portfolio, holdings, allocation, and snapshot persistence (Feature 009)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import (
    PortfolioAllocationRow,
    PortfolioHoldingRow,
    PortfolioRow,
    PortfolioSnapshotRow,
)
from app.portfolio import identity

PORTFOLIO_ID = 1
QUOTE_ASSET = identity.QUOTE_ASSET
LOCAL_MANUAL = "local_manual"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_portfolio(db: Session) -> PortfolioRow | None:
    return db.get(PortfolioRow, PORTFOLIO_ID)


def ensure_portfolio(db: Session) -> PortfolioRow:
    row = get_portfolio(db)
    if row is not None:
        return row
    now = _now()
    row = PortfolioRow(
        id=PORTFOLIO_ID,
        cash="0",
        deployed="0",
        realized_pnl="0",
        unrealized_pnl="0",
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def touch_portfolio(db: Session) -> PortfolioRow:
    row = ensure_portfolio(db)
    row.updated_at = _now()
    db.flush()
    return row


def sync_cash_cache(db: Session, cash: str) -> None:
    """Keep leftover portfolio.cash in sync; holdings remain authoritative."""
    row = ensure_portfolio(db)
    row.cash = cash
    row.updated_at = _now()
    db.flush()


def migrate_cash_to_usdt(db: Session) -> bool:
    """Copy leftover portfolio.cash into a usdt holding once. Returns True if a row was added."""
    portfolio = get_portfolio(db)
    if portfolio is None:
        return False
    if get_holding(db, QUOTE_ASSET) is not None:
        return False
    try:
        qty = identity.parse_money(portfolio.cash)
    except identity.CapitalIdentityError:
        return False
    if qty <= 0:
        return False
    upsert_holding(
        db,
        asset=QUOTE_ASSET,
        quantity=identity.money_str(qty),
        average_cost="1",
        provenance=LOCAL_MANUAL,
    )
    return True


def list_holdings(db: Session) -> list[PortfolioHoldingRow]:
    rows = (
        db.query(PortfolioHoldingRow)
        .filter(PortfolioHoldingRow.portfolio_id == PORTFOLIO_ID)
        .all()
    )
    rows.sort(key=lambda r: (0 if r.asset == QUOTE_ASSET else 1, r.asset))
    return rows


def holding_assets(db: Session) -> list[str]:
    return [row.asset for row in list_holdings(db)]


def get_holding(db: Session, asset: str) -> PortfolioHoldingRow | None:
    code = asset.lower().strip()
    return (
        db.query(PortfolioHoldingRow)
        .filter(
            PortfolioHoldingRow.portfolio_id == PORTFOLIO_ID,
            PortfolioHoldingRow.asset == code,
        )
        .one_or_none()
    )


def upsert_holding(
    db: Session,
    *,
    asset: str,
    quantity: str,
    average_cost: str | None,
    provenance: str = LOCAL_MANUAL,
) -> PortfolioHoldingRow:
    code = asset.lower().strip()
    now = _now()
    row = get_holding(db, code)
    if row is None:
        row = PortfolioHoldingRow(
            id=str(uuid4()),
            portfolio_id=PORTFOLIO_ID,
            asset=code,
            quantity=quantity,
            average_cost=average_cost,
            realized_pnl="0",
            provenance=provenance,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.quantity = quantity
        row.average_cost = average_cost
        row.updated_at = now
    touch_portfolio(db)
    db.flush()
    return row


def delete_holding(db: Session, asset: str) -> bool:
    row = get_holding(db, asset)
    if row is None:
        return False
    db.delete(row)
    touch_portfolio(db)
    db.flush()
    return True


def usdt_quantity(db: Session) -> str | None:
    row = get_holding(db, QUOTE_ASSET)
    if row is None:
        return None
    return row.quantity


def list_allocations(db: Session) -> list[PortfolioAllocationRow]:
    return (
        db.query(PortfolioAllocationRow)
        .filter(PortfolioAllocationRow.portfolio_id == PORTFOLIO_ID)
        .order_by(PortfolioAllocationRow.created_at.asc())
        .all()
    )


def get_allocation(db: Session, allocation_id: str) -> PortfolioAllocationRow | None:
    return db.get(PortfolioAllocationRow, allocation_id)


def create_allocation(
    db: Session,
    *,
    label: str,
    reserved_size: str,
    target_ref: str | None,
) -> PortfolioAllocationRow:
    ensure_portfolio(db)
    now = _now()
    row = PortfolioAllocationRow(
        id=str(uuid4()),
        portfolio_id=PORTFOLIO_ID,
        label=label,
        reserved_size=reserved_size,
        target_ref=target_ref,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    touch_portfolio(db)
    db.flush()
    return row


def update_allocation_size(db: Session, allocation_id: str, reserved_size: str) -> PortfolioAllocationRow | None:
    row = get_allocation(db, allocation_id)
    if row is None:
        return None
    row.reserved_size = reserved_size
    row.updated_at = _now()
    touch_portfolio(db)
    db.flush()
    return row


def delete_allocation(db: Session, allocation_id: str) -> bool:
    row = get_allocation(db, allocation_id)
    if row is None:
        return False
    db.delete(row)
    touch_portfolio(db)
    db.flush()
    return True


def append_snapshot(db: Session, *, reason: str, payload: dict) -> PortfolioSnapshotRow:
    """Append one historical snapshot in the current transaction. Callers commit once."""
    row = PortfolioSnapshotRow(
        id=str(uuid4()),
        created_at=_now(),
        reason=reason,
        payload=json.dumps(payload),
    )
    db.add(row)
    db.flush()
    return row


def count_snapshots(db: Session) -> int:
    return db.query(PortfolioSnapshotRow).count()


def list_snapshot_reasons(db: Session) -> list[str]:
    rows = (
        db.query(PortfolioSnapshotRow)
        .order_by(PortfolioSnapshotRow.created_at.asc())
        .all()
    )
    return [row.reason for row in rows]
