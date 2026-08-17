"""Build Feature 010 portfolio RiskContext fields from Portfolio + session."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.portfolio import identity
from app.portfolio import repository as portfolio_repo
from app.portfolio import service as portfolio_svc
from app.portfolio.valuation import QuoteView
from app.simulation.control.risk import HoldingValueView
from app.simulation.money import d
from app.simulation.state_machine import SessionState


def base_asset_from_symbol(symbol: str) -> str:
    return portfolio_svc.asset_from_symbol(symbol)


def portfolio_available_amount(db: Session) -> Decimal:
    portfolio_repo.ensure_portfolio(db)
    portfolio_repo.migrate_cash_to_usdt(db)
    cash = portfolio_svc.quote_cash_amount(db)
    reserved = Decimal("0")
    for a in portfolio_repo.list_allocations(db):
        reserved += identity.parse_money(a.reserved_size)
    return identity.available_from(cash, reserved)


def sessions_bound_to_allocation(db: Session, allocation_id: str) -> list[SimulationSessionRow]:
    active_states = (
        SessionState.CONFIGURED.value,
        SessionState.RUNNING.value,
        SessionState.STOPPING.value,
        SessionState.RECOVERY_BLOCKED.value,
    )
    return (
        db.query(SimulationSessionRow)
        .filter(
            SimulationSessionRow.allocation_id == allocation_id,
            SimulationSessionRow.state.in_(active_states),
        )
        .all()
    )


def binding_deployed(row: SimulationSessionRow) -> Decimal:
    if row.position_side == "long" and row.cost_basis:
        return d(row.cost_basis)
    return Decimal("0")


def holdings_value_views(snapshot: dict) -> list[HoldingValueView]:
    out: list[HoldingValueView] = []
    for h in snapshot.get("holdings") or []:
        asset = str(h["asset"]).lower()
        qty = d(h["quantity"])
        mv = h.get("marketValue")
        out.append(
            HoldingValueView(
                asset=asset,
                quantity=qty,
                market_value=d(mv) if mv is not None else None,
            )
        )
    return out


def freeze_portfolio_loss_baseline(
    db: Session,
    row: SimulationSessionRow,
    quotes: dict[str, QuoteView] | None = None,
) -> None:
    """Persist baseline kind/value at start when portfolio max-loss is configured."""
    if not row.portfolio_max_loss_rate and not row.portfolio_max_loss_amount:
        return
    snap = portfolio_svc.build_snapshot(db, quotes=quotes)
    if snap.get("equityComplete") is True and snap.get("equity") is not None:
        kind = "equity"
        value = d(snap["equity"])
    else:
        kind = "quote_cash"
        value = d(snap["cash"])
    row.portfolio_loss_baseline_kind = kind
    row.portfolio_loss_baseline_value = identity.money_str(value)
    # Derive amount from rate if amount missing
    if row.portfolio_max_loss_amount is None and row.portfolio_max_loss_rate:
        amount = value * d(row.portfolio_max_loss_rate)
        row.portfolio_max_loss_amount = identity.money_str(amount)


async def load_holding_quotes(db: Session) -> dict[str, QuoteView]:
    """Feature 002 public quotes for current Portfolio holding assets."""
    from app.portfolio import repository as portfolio_repo
    from app.portfolio.valuation import fetch_quotes

    return await fetch_quotes(portfolio_repo.holding_assets(db))


def apply_portfolio_context(
    ctx_kwargs: dict,
    *,
    db: Session,
    row: SimulationSessionRow,
    quotes: dict[str, QuoteView] | None = None,
) -> dict:
    """Mutate/return kwargs kwargs with portfolio context enabled for Simulation."""
    snap = portfolio_svc.build_snapshot(db, quotes=quotes)
    ctx_kwargs["portfolio_context_enabled"] = True
    ctx_kwargs["allocated_capital"] = d(row.allocated_capital)
    ctx_kwargs["max_position_size"] = d(row.max_position_size)
    ctx_kwargs["trade_asset"] = base_asset_from_symbol(row.symbol)
    ctx_kwargs["holdings"] = holdings_value_views(snap)
    ctx_kwargs["portfolio_equity_complete"] = bool(snap.get("equityComplete"))
    ctx_kwargs["portfolio_current_equity"] = d(snap["equity"]) if snap.get("equity") is not None else None
    ctx_kwargs["portfolio_quote_cash"] = d(snap["cash"]) if snap.get("cash") is not None else None
    if row.allocation_id:
        alloc = portfolio_repo.get_allocation(db, row.allocation_id)
        ctx_kwargs["allocation_id"] = row.allocation_id
        if alloc is not None:
            ctx_kwargs["allocation_reserved"] = d(alloc.reserved_size)
        ctx_kwargs["allocation_deployed"] = binding_deployed(row)
    if row.portfolio_max_loss_amount:
        ctx_kwargs["portfolio_max_loss_amount"] = d(row.portfolio_max_loss_amount)
    if row.portfolio_loss_baseline_kind:
        ctx_kwargs["portfolio_loss_baseline_kind"] = row.portfolio_loss_baseline_kind
    if row.portfolio_loss_baseline_value:
        ctx_kwargs["portfolio_loss_baseline_value"] = d(row.portfolio_loss_baseline_value)
    if row.per_symbol_max_weight:
        ctx_kwargs["per_symbol_max_weight"] = d(row.per_symbol_max_weight)
    return ctx_kwargs
