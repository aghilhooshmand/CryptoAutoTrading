"""Portfolio domain service (Feature 009)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import PortfolioAllocationRow
from app.portfolio import identity, repository as repo


class PortfolioError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _iso(dt) -> str:
    if dt is None:
        return ""
    text = dt.isoformat()
    if text.endswith("+00:00"):
        return text[:-6] + "Z"
    if dt.tzinfo is None:
        return text + "Z"
    return text


def _allocation_dict(row: PortfolioAllocationRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "label": row.label,
        "reservedSize": row.reserved_size,
        "targetRef": row.target_ref,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


CORRUPT_ALLOCATION_MSG = (
    "Stored allocation capital is corrupt; refusing to invent balances."
)
CORRUPT_PORTFOLIO_MSG = "Stored portfolio capital is corrupt; refusing to invent balances."
CORRUPT_MUTATION_MSG = (
    "Stored allocation capital is corrupt; release or repair allocations "
    "before changing funding or reservations."
)


def _safe_money(raw: str, field: str) -> Decimal | None:
    try:
        return identity.parse_money(raw)
    except identity.CapitalIdentityError:
        return None


def _parse_cash_or_error(raw: str) -> Decimal:
    try:
        return identity.parse_money(raw)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", CORRUPT_PORTFOLIO_MSG) from exc


def _sum_reserved_or_error(sizes: list[str]) -> Decimal:
    try:
        return identity.sum_reserved(sizes)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", CORRUPT_MUTATION_MSG) from exc


def build_snapshot(db: Session) -> dict[str, Any]:
    """Read portfolio; fail closed with warning if stored money is corrupt."""
    row = repo.get_portfolio(db)
    allocations = repo.list_allocations(db)

    warning: str | None = None
    if row is None:
        cash = Decimal("0")
        realized = Decimal("0")
        unrealized = Decimal("0")
        updated_at = None
    else:
        cash_v = _safe_money(row.cash, "cash")
        deployed_v = _safe_money(row.deployed, "deployed")
        realized_v = _safe_money(row.realized_pnl, "realizedPnl")
        unrealized_v = _safe_money(row.unrealized_pnl, "unrealizedPnl")
        if None in (cash_v, deployed_v, realized_v, unrealized_v):
            warning = CORRUPT_PORTFOLIO_MSG
            cash = Decimal("0")
            realized = Decimal("0")
            unrealized = Decimal("0")
        else:
            cash = cash_v  # type: ignore[assignment]
            realized = realized_v  # type: ignore[assignment]
            unrealized = unrealized_v  # type: ignore[assignment]
        updated_at = row.updated_at

    reserved_sizes: list[str] = []
    allocation_out: list[dict[str, Any]] = []
    allocation_corrupt = False
    for a in allocations:
        # Keep corrupt rows visible so the operator can inspect/release them.
        allocation_out.append(_allocation_dict(a))
        size_v = _safe_money(a.reserved_size, "reservedSize")
        if size_v is None:
            allocation_corrupt = True
            continue
        reserved_sizes.append(a.reserved_size)

    if allocation_corrupt:
        # Do not understate reserved by summing only valid rows — that invents available.
        warning = warning or CORRUPT_ALLOCATION_MSG
        reserved = Decimal("0")
        available = Decimal("0")
    else:
        try:
            reserved = identity.sum_reserved(reserved_sizes) if reserved_sizes else Decimal("0")
            if warning is None:
                available = identity.assert_invariants(cash, reserved)
            else:
                available = identity.available_from(cash, reserved)
                if available < 0:
                    available = Decimal("0")
        except identity.CapitalIdentityError as exc:
            warning = warning or exc.message
            reserved = identity.sum_reserved(reserved_sizes) if reserved_sizes else Decimal("0")
            available = Decimal("0")

    # Feature 009: deployed always 0, positions empty, equity flat = cash
    return {
        "cash": identity.money_str(cash),
        "reserved": identity.money_str(reserved),
        "available": identity.money_str(available),
        "deployed": "0",
        "realizedPnl": identity.money_str(realized),
        "unrealizedPnl": identity.money_str(unrealized),
        "equity": identity.money_str(cash),
        "positions": [],
        "allocations": allocation_out,
        "updatedAt": _iso(updated_at) if updated_at else None,
        "warning": warning,
    }


def set_funding(db: Session, cash_raw: str) -> dict[str, Any]:
    try:
        cash = identity.parse_money(cash_raw)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if cash < 0:
        raise PortfolioError("invalid_config", "Cash cannot be negative")

    repo.ensure_portfolio(db)
    allocations = repo.list_allocations(db)
    reserved = _sum_reserved_or_error([a.reserved_size for a in allocations])
    try:
        identity.assert_invariants(cash, reserved)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError(
            "invalid_config",
            "Cash cannot be less than reserved capital. Resize or release allocations first.",
        ) from exc

    repo.set_cash(db, identity.money_str(cash))
    return build_snapshot(db)


def create_allocation(
    db: Session,
    *,
    label: str,
    reserved_size: str,
    target_ref: str | None,
) -> dict[str, Any]:
    label_clean = (label or "").strip()
    if not label_clean:
        raise PortfolioError("invalid_config", "Allocation label is required")

    try:
        size = identity.parse_money(reserved_size)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if size <= 0:
        raise PortfolioError("invalid_config", "Reserved size must be greater than zero")

    portfolio = repo.ensure_portfolio(db)
    cash = _parse_cash_or_error(portfolio.cash)
    existing = repo.list_allocations(db)
    reserved = _sum_reserved_or_error([a.reserved_size for a in existing]) + size
    try:
        identity.assert_invariants(cash, reserved)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError(
            "invalid_config",
            "Reserved capital cannot exceed cash.",
        ) from exc

    target = (target_ref or "").strip() or None
    repo.create_allocation(
        db,
        label=label_clean,
        reserved_size=identity.money_str(size),
        target_ref=target,
    )
    return build_snapshot(db)


def resize_allocation(db: Session, allocation_id: str, reserved_size: str) -> dict[str, Any]:
    row = repo.get_allocation(db, allocation_id)
    if row is None:
        raise PortfolioError("not_found", "Allocation not found", http_status=404)

    try:
        size = identity.parse_money(reserved_size)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if size <= 0:
        raise PortfolioError("invalid_config", "Reserved size must be greater than zero")

    portfolio = repo.ensure_portfolio(db)
    cash = _parse_cash_or_error(portfolio.cash)
    others = [a for a in repo.list_allocations(db) if a.id != allocation_id]
    reserved = _sum_reserved_or_error([a.reserved_size for a in others]) + size
    try:
        identity.assert_invariants(cash, reserved)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError(
            "invalid_config",
            "Reserved capital cannot exceed cash.",
        ) from exc

    repo.update_allocation_size(db, allocation_id, identity.money_str(size))
    return build_snapshot(db)


def release_allocation(db: Session, allocation_id: str) -> dict[str, Any]:
    if not repo.delete_allocation(db, allocation_id):
        raise PortfolioError("not_found", "Allocation not found", http_status=404)
    return build_snapshot(db)
