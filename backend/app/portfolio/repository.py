"""Portfolio and allocation persistence (Feature 009)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import PortfolioAllocationRow, PortfolioRow

PORTFOLIO_ID = 1


def get_portfolio(db: Session) -> PortfolioRow | None:
    return db.get(PortfolioRow, PORTFOLIO_ID)


def ensure_portfolio(db: Session) -> PortfolioRow:
    row = get_portfolio(db)
    if row is not None:
        return row
    now = datetime.now(timezone.utc)
    row = PortfolioRow(
        id=PORTFOLIO_ID,
        cash="0",
        deployed="0",
        realized_pnl="0",
        unrealized_pnl="0",
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_cash(db: Session, cash: str) -> PortfolioRow:
    row = ensure_portfolio(db)
    row.cash = cash
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


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
    now = datetime.now(timezone.utc)
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
    portfolio = get_portfolio(db)
    if portfolio is not None:
        portfolio.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def update_allocation_size(db: Session, allocation_id: str, reserved_size: str) -> PortfolioAllocationRow | None:
    row = get_allocation(db, allocation_id)
    if row is None:
        return None
    now = datetime.now(timezone.utc)
    row.reserved_size = reserved_size
    row.updated_at = now
    portfolio = get_portfolio(db)
    if portfolio is not None:
        portfolio.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def delete_allocation(db: Session, allocation_id: str) -> bool:
    row = get_allocation(db, allocation_id)
    if row is None:
        return False
    db.delete(row)
    portfolio = get_portfolio(db)
    if portfolio is not None:
        portfolio.updated_at = datetime.now(timezone.utc)
    db.commit()
    return True
