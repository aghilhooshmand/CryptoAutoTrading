"""Capital identity helpers: available = quote_cash − reserved (Feature 009)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.simulation.money import as_str, d

QUOTE_ASSET = "usdt"


class CapitalIdentityError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_money(raw: str | int | float | Decimal) -> Decimal:
    try:
        value = d(raw)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise CapitalIdentityError(f"Invalid money amount: {raw}") from exc
    if not value.is_finite():
        raise CapitalIdentityError(f"Invalid money amount: {raw}")
    return value


def quote_cash_from_usdt_quantity(quantity: str | None) -> Decimal:
    """Quote cash is the USDT holding quantity, or 0 if none."""
    if quantity is None:
        return Decimal("0")
    return parse_money(quantity)


def sum_reserved(sizes: list[str]) -> Decimal:
    total = Decimal("0")
    for size in sizes:
        total += parse_money(size)
    return total


def sum_market_values(values: list[Decimal]) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += value
    return total


def equity_complete(unvalued_assets: list[str]) -> bool:
    return len(unvalued_assets) == 0


def available_from(cash: Decimal, reserved: Decimal) -> Decimal:
    return cash - reserved


def assert_invariants(cash: Decimal, reserved: Decimal) -> Decimal:
    """Return available; raise if cash/reserved violate Feature 009 identity."""
    if cash < 0:
        raise CapitalIdentityError("Cash cannot be negative")
    if reserved < 0:
        raise CapitalIdentityError("Reserved capital cannot be negative")
    if reserved > cash:
        raise CapitalIdentityError("Reserved capital cannot exceed cash")
    available = available_from(cash, reserved)
    if available < 0:
        raise CapitalIdentityError("Available capital cannot be negative")
    return available


def money_str(value: Decimal) -> str:
    return as_str(value)


def weight_str(market_value: Decimal, equity: Decimal) -> str | None:
    if equity <= 0:
        return None
    return money_str(market_value / equity)


def total_pnl(realized: Decimal, unrealized: Decimal | None) -> Decimal | None:
    """Combined P&L only when unrealized is defined (not invented)."""
    if unrealized is None:
        return None
    return realized + unrealized


def total_return(pnl: Decimal | None, cost_basis: Decimal | None) -> Decimal | None:
    """Portfolio return only when total P&L and a positive cost basis both exist."""
    if pnl is None or cost_basis is None or cost_basis <= 0:
        return None
    return pnl / cost_basis
