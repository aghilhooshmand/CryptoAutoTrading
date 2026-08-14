"""Portfolio domain service (Feature 009)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import PortfolioAllocationRow, PortfolioHoldingRow, SimulationSessionRow
from app.portfolio import identity, repository as repo
from app.portfolio.valuation import QuoteView, usdt_quote

QUOTE_ASSET = identity.QUOTE_ASSET
SIMULATION = "simulation"
BOOK_PROVENANCE = "simulation"
FILL_APPLY_INSUFFICIENT = (
    "Simulation Portfolio could not apply the last fill: insufficient USDT."
)
FILL_APPLY_QTY = (
    "Simulation Portfolio could not apply the last fill: insufficient holding quantity."
)
ACTIVE_SESSION_STATES = ("RUNNING", "STOPPING")


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


def _safe_money(raw: str) -> Decimal | None:
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


def quote_cash_amount(db: Session) -> Decimal:
    """Authoritative quote cash from the USDT holding (0 if none)."""
    qty = repo.usdt_quantity(db)
    if qty is None:
        return Decimal("0")
    return _parse_cash_or_error(qty)


def asset_from_symbol(symbol: str) -> str:
    code = (symbol or "").strip().lower()
    if code.endswith("_usdt") and len(code) > 5:
        return code[: -len("_usdt")]
    if "_" in code:
        return code.split("_", 1)[0]
    return code


def prepare_read(db: Session) -> None:
    """Persist leftover cash→USDT and provenance migration if needed. Does not snapshot."""
    if repo.get_portfolio(db) is None:
        return
    changed = repo.migrate_cash_to_usdt(db)
    changed = repo.migrate_provenance(db) > 0 or changed
    if changed:
        db.commit()


def _holding_view(row: PortfolioHoldingRow, quotes: dict[str, QuoteView], equity: Decimal) -> dict[str, Any]:
    asset = row.asset
    quote = quotes.get(asset)
    if asset == QUOTE_ASSET:
        quote = quote or usdt_quote()

    quantity = _safe_money(row.quantity)
    avg = None if row.average_cost in (None, "") else _safe_money(row.average_cost)
    realized_raw = _safe_money(row.realized_pnl)
    realized = identity.money_str(realized_raw) if realized_raw is not None else "0"

    price: str | None = None
    price_status = "unavailable"
    market_value: str | None = None
    weight: str | None = None
    unrealized: str | None = None
    ret: str | None = None

    if quantity is not None and quote is not None and quote.price is not None:
        price_status = quote.status
        price = identity.money_str(quote.price)
        value = quantity * quote.price
        market_value = identity.money_str(value)
        weight = identity.weight_str(value, equity)
        if asset != QUOTE_ASSET and avg is not None:
            cost = quantity * avg
            u = value - cost
            unrealized = identity.money_str(u)
            if cost != 0:
                ret = identity.money_str(u / cost)
            else:
                ret = None

    provenance = row.provenance or SIMULATION
    if provenance == "local_manual":
        provenance = SIMULATION

    return {
        "id": row.id,
        "asset": asset,
        "quantity": row.quantity,
        "averageCost": None if row.average_cost in (None, "") else row.average_cost,
        "price": price,
        "priceStatus": price_status,
        "marketValue": market_value,
        "weight": weight,
        "realizedPnl": realized,
        "unrealizedPnl": unrealized,
        "return": ret,
        "provenance": provenance,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def _project_positions(db: Session) -> tuple[str, list[dict[str, Any]]]:
    rows = (
        db.query(SimulationSessionRow)
        .filter(
            SimulationSessionRow.state.in_(ACTIVE_SESSION_STATES),
            SimulationSessionRow.position_side == "long",
        )
        .all()
    )
    positions: list[dict[str, Any]] = []
    deployed = Decimal("0")
    for row in rows:
        cost = None if row.cost_basis in (None, "") else _safe_money(row.cost_basis)
        if cost is not None:
            deployed += cost
        positions.append(
            {
                "sessionId": row.id,
                "symbol": row.symbol,
                "asset": asset_from_symbol(row.symbol),
                "side": "long",
                "quantity": row.position_qty,
                "costBasis": row.cost_basis,
            }
        )
    return identity.money_str(deployed) if positions else "0", positions


def build_snapshot(db: Session, quotes: dict[str, QuoteView] | None = None) -> dict[str, Any]:
    """Read portfolio; fail closed with warning if stored money is corrupt.

    GET must not insert historical snapshot rows. Callers that mutate the book
    append a snapshot separately in the same transaction.
    """
    quotes = quotes or {}
    repo.ensure_portfolio(db)
    repo.migrate_cash_to_usdt(db)
    repo.migrate_provenance(db)

    holdings = repo.list_holdings(db)
    allocations = repo.list_allocations(db)
    portfolio = repo.get_portfolio(db)
    updated_at = portfolio.updated_at if portfolio is not None else None
    fill_warning = portfolio.fill_apply_warning if portfolio is not None else None

    warning: str | None = None
    cash = Decimal("0")
    usdt_row = repo.get_holding(db, QUOTE_ASSET)
    if usdt_row is not None:
        cash_v = _safe_money(usdt_row.quantity)
        if cash_v is None:
            warning = CORRUPT_PORTFOLIO_MSG
            cash = Decimal("0")
        else:
            cash = cash_v
    elif portfolio is not None:
        leftover = _safe_money(portfolio.cash)
        if leftover is None:
            warning = CORRUPT_PORTFOLIO_MSG
            cash = Decimal("0")

    reserved_sizes: list[str] = []
    allocation_out: list[dict[str, Any]] = []
    allocation_corrupt = False
    for a in allocations:
        allocation_out.append(_allocation_dict(a))
        size_v = _safe_money(a.reserved_size)
        if size_v is None:
            allocation_corrupt = True
            continue
        reserved_sizes.append(a.reserved_size)

    if allocation_corrupt:
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

    valued: list[Decimal] = []
    unvalued_assets: list[str] = []
    holding_corrupt = False
    prepared: list[tuple[PortfolioHoldingRow, Decimal | None, QuoteView | None]] = []
    for row in holdings:
        qty = _safe_money(row.quantity)
        if qty is None:
            holding_corrupt = True
            prepared.append((row, None, quotes.get(row.asset)))
            continue
        quote = quotes.get(row.asset)
        if row.asset == QUOTE_ASSET:
            quote = quote or usdt_quote()
        if quote is not None and quote.price is not None:
            valued.append(qty * quote.price)
        else:
            unvalued_assets.append(row.asset)
        prepared.append((row, qty, quote))

    if holding_corrupt:
        warning = warning or CORRUPT_PORTFOLIO_MSG

    equity = identity.sum_market_values(valued)
    complete = identity.equity_complete(unvalued_assets) and not holding_corrupt

    holding_out: list[dict[str, Any]] = []
    known_unrealized = Decimal("0")
    known_realized = Decimal("0")
    for row, _qty, _quote in prepared:
        view = _holding_view(row, quotes, equity)
        holding_out.append(view)
        if view["asset"] != QUOTE_ASSET:
            u = view["unrealizedPnl"]
            if u is not None:
                parsed_u = _safe_money(u)
                if parsed_u is not None:
                    known_unrealized += parsed_u
        r = _safe_money(view["realizedPnl"])
        if r is not None:
            known_realized += r

    non_quote = [view for view in holding_out if view["asset"] != QUOTE_ASSET]
    pnl_defined = all(view["unrealizedPnl"] is not None for view in non_quote)
    cost_basis = Decimal("0")
    if pnl_defined:
        for view in holding_out:
            qty = _safe_money(view["quantity"])
            avg_raw = view["averageCost"]
            avg = None if avg_raw in (None, "") else _safe_money(str(avg_raw))
            if qty is not None and avg is not None:
                cost_basis += qty * avg
        combined = identity.total_pnl(known_realized, known_unrealized)
        total_pnl_out = identity.money_str(combined) if combined is not None else None
        ret = identity.total_return(combined, cost_basis)
        total_return_out = identity.money_str(ret) if ret is not None else None
    else:
        total_pnl_out = None
        total_return_out = None

    deployed, positions = _project_positions(db)
    if warning is None and fill_warning:
        warning = fill_warning

    return {
        "quoteCurrency": QUOTE_ASSET,
        "bookProvenance": BOOK_PROVENANCE,
        "mode": "simulation",
        "cash": identity.money_str(cash),
        "reserved": identity.money_str(reserved),
        "available": identity.money_str(available),
        "deployed": deployed,
        "realizedPnl": identity.money_str(known_realized),
        "unrealizedPnl": identity.money_str(known_unrealized),
        "totalPnl": total_pnl_out,
        "totalReturn": total_return_out,
        "equity": identity.money_str(equity),
        "equityComplete": complete,
        "unvaluedAssets": unvalued_assets,
        "positions": positions,
        "holdings": holding_out,
        "allocations": allocation_out,
        "updatedAt": _iso(updated_at) if updated_at else None,
        "warning": warning,
    }


def _commit_with_snapshot(
    db: Session,
    reason: str,
    quotes: dict[str, QuoteView] | None,
) -> dict[str, Any]:
    snap = build_snapshot(db, quotes)
    repo.append_snapshot(db, reason=reason, payload=snap)
    db.commit()
    return snap


def _set_usdt_quantity(db: Session, cash: Decimal) -> None:
    if cash == 0:
        repo.delete_holding(db, QUOTE_ASSET)
        repo.sync_cash_cache(db, "0")
        return
    repo.upsert_holding(
        db,
        asset=QUOTE_ASSET,
        quantity=identity.money_str(cash),
        average_cost="1",
        provenance=SIMULATION,
    )
    repo.sync_cash_cache(db, identity.money_str(cash))


def _apply_funding(db: Session, cash_raw: str) -> None:
    try:
        cash = identity.parse_money(cash_raw)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if cash < 0:
        raise PortfolioError("invalid_config", "Cash cannot be negative")

    repo.ensure_portfolio(db)
    repo.migrate_cash_to_usdt(db)
    repo.migrate_provenance(db)
    allocations = repo.list_allocations(db)
    reserved = _sum_reserved_or_error([a.reserved_size for a in allocations])
    try:
        identity.assert_invariants(cash, reserved)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError(
            "invalid_config",
            "Cash cannot be less than reserved capital. Resize or release allocations first.",
        ) from exc

    _set_usdt_quantity(db, cash)


def set_funding(db: Session, cash_raw: str, quotes: dict[str, QuoteView] | None = None) -> dict[str, Any]:
    _apply_funding(db, cash_raw)
    return _commit_with_snapshot(db, "funding", quotes)


def try_apply_simulation_fill(
    db: Session,
    *,
    side: str,
    qty: Decimal | str,
    cash_delta: Decimal | str,
    fill_price: Decimal | str,
    asset: str | None = None,
    symbol: str | None = None,
    quotes: dict[str, QuoteView] | None = None,
) -> dict[str, Any] | None:
    """Apply a simulated fill to the book. Does not commit. Returns snapshot or None if refused."""
    repo.ensure_portfolio(db)
    repo.migrate_cash_to_usdt(db)
    repo.migrate_provenance(db)

    code = (asset or asset_from_symbol(symbol or "")).strip().lower()
    if not code or code == QUOTE_ASSET:
        repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
        return None

    try:
        qty_d = identity.parse_money(qty)
        delta = identity.parse_money(cash_delta)
        price = identity.parse_money(fill_price)
    except identity.CapitalIdentityError:
        repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
        return None
    if qty_d <= 0:
        repo.set_fill_apply_warning(db, FILL_APPLY_QTY)
        return None

    side_u = (side or "").strip().upper()
    cash = quote_cash_amount(db)
    new_cash = cash + delta
    allocations = repo.list_allocations(db)
    try:
        reserved = _sum_reserved_or_error([a.reserved_size for a in allocations])
    except PortfolioError:
        repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
        return None
    if new_cash < 0 or new_cash < reserved:
        repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
        return None

    if side_u == "BUY":
        existing = repo.get_holding(db, code)
        if existing is None:
            new_qty = qty_d
            new_avg: str | None = identity.money_str(price)
            realized = "0"
        else:
            old_qty = _safe_money(existing.quantity)
            if old_qty is None:
                repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
                return None
            new_qty = old_qty + qty_d
            old_avg = None if existing.average_cost in (None, "") else _safe_money(existing.average_cost)
            if old_avg is None:
                new_avg = None
            else:
                new_avg = identity.money_str((old_qty * old_avg + qty_d * price) / new_qty)
            realized = existing.realized_pnl
        _set_usdt_quantity(db, new_cash)
        repo.upsert_holding(
            db,
            asset=code,
            quantity=identity.money_str(new_qty),
            average_cost=new_avg,
            provenance=SIMULATION,
            realized_pnl=realized,
        )
    elif side_u == "SELL":
        existing = repo.get_holding(db, code)
        if existing is None:
            repo.set_fill_apply_warning(db, FILL_APPLY_QTY)
            return None
        old_qty = _safe_money(existing.quantity)
        if old_qty is None or qty_d > old_qty:
            repo.set_fill_apply_warning(db, FILL_APPLY_QTY)
            return None
        old_avg = None if existing.average_cost in (None, "") else _safe_money(existing.average_cost)
        realized_raw = _safe_money(existing.realized_pnl) or Decimal("0")
        if old_avg is not None:
            realized_raw += (price - old_avg) * qty_d
        new_qty = old_qty - qty_d
        _set_usdt_quantity(db, new_cash)
        if new_qty == 0:
            usdt = repo.get_holding(db, QUOTE_ASSET)
            if usdt is not None:
                usdt_realized = _safe_money(usdt.realized_pnl) or Decimal("0")
                repo.upsert_holding(
                    db,
                    asset=QUOTE_ASSET,
                    quantity=usdt.quantity,
                    average_cost=usdt.average_cost,
                    provenance=SIMULATION,
                    realized_pnl=identity.money_str(usdt_realized + realized_raw),
                )
            repo.delete_holding(db, code)
        else:
            repo.upsert_holding(
                db,
                asset=code,
                quantity=identity.money_str(new_qty),
                average_cost=existing.average_cost,
                provenance=SIMULATION,
                realized_pnl=identity.money_str(realized_raw),
            )
    else:
        repo.set_fill_apply_warning(db, FILL_APPLY_INSUFFICIENT)
        return None

    repo.set_fill_apply_warning(db, None)
    snap = build_snapshot(db, quotes)
    repo.append_snapshot(db, reason="simulation_fill", payload=snap)
    return snap


def apply_simulation_fill(
    db: Session,
    *,
    side: str,
    qty: Decimal | str,
    cash_delta: Decimal | str,
    fill_price: Decimal | str,
    asset: str | None = None,
    symbol: str | None = None,
    quotes: dict[str, QuoteView] | None = None,
) -> dict[str, Any] | None:
    """Test/helper entry: apply fill and commit (warning-only commit on refuse)."""
    snap = try_apply_simulation_fill(
        db,
        side=side,
        qty=qty,
        cash_delta=cash_delta,
        fill_price=fill_price,
        asset=asset,
        symbol=symbol,
        quotes=quotes,
    )
    db.commit()
    return snap


def _apply_create_allocation(
    db: Session,
    *,
    label: str,
    reserved_size: str,
    target_ref: str | None,
) -> None:
    label_clean = (label or "").strip()
    if not label_clean:
        raise PortfolioError("invalid_config", "Allocation label is required")

    try:
        size = identity.parse_money(reserved_size)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if size <= 0:
        raise PortfolioError("invalid_config", "Reserved size must be greater than zero")

    repo.ensure_portfolio(db)
    repo.migrate_cash_to_usdt(db)
    cash = quote_cash_amount(db)
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


def create_allocation(
    db: Session,
    *,
    label: str,
    reserved_size: str,
    target_ref: str | None,
    quotes: dict[str, QuoteView] | None = None,
) -> dict[str, Any]:
    _apply_create_allocation(db, label=label, reserved_size=reserved_size, target_ref=target_ref)
    return _commit_with_snapshot(db, "allocation_create", quotes)


def _apply_resize_allocation(db: Session, allocation_id: str, reserved_size: str) -> None:
    row = repo.get_allocation(db, allocation_id)
    if row is None:
        raise PortfolioError("not_found", "Allocation not found", http_status=404)

    try:
        size = identity.parse_money(reserved_size)
    except identity.CapitalIdentityError as exc:
        raise PortfolioError("invalid_config", exc.message) from exc
    if size <= 0:
        raise PortfolioError("invalid_config", "Reserved size must be greater than zero")

    repo.ensure_portfolio(db)
    repo.migrate_cash_to_usdt(db)
    cash = quote_cash_amount(db)
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


def resize_allocation(
    db: Session,
    allocation_id: str,
    reserved_size: str,
    quotes: dict[str, QuoteView] | None = None,
) -> dict[str, Any]:
    _apply_resize_allocation(db, allocation_id, reserved_size)
    return _commit_with_snapshot(db, "allocation_resize", quotes)


def _apply_release_allocation(db: Session, allocation_id: str) -> None:
    if not repo.delete_allocation(db, allocation_id):
        raise PortfolioError("not_found", "Allocation not found", http_status=404)


def release_allocation(
    db: Session,
    allocation_id: str,
    quotes: dict[str, QuoteView] | None = None,
) -> dict[str, Any]:
    _apply_release_allocation(db, allocation_id)
    return _commit_with_snapshot(db, "allocation_release", quotes)


async def snapshot_after(
    db: Session,
    reason: str,
    apply_fn,
    fetch_quotes,
) -> dict[str, Any]:
    """Apply a book mutation, value holdings, append one snapshot, commit once."""
    apply_fn()
    quotes = await fetch_quotes(repo.holding_assets(db))
    return _commit_with_snapshot(db, reason, quotes)
