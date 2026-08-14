"""Capital identity helpers: available = cash − reserved (Feature 009)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.simulation.money import as_str, d


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


def sum_reserved(sizes: list[str]) -> Decimal:
    total = Decimal("0")
    for size in sizes:
        total += parse_money(size)
    return total


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
