"""Position sizing for long-only full BUY."""

from __future__ import annotations

from decimal import Decimal

from app.simulation.money import DUST_NOTIONAL, d, quantize_money


def affordable_notional(cash: Decimal, fee_rate: Decimal) -> Decimal:
    return quantize_money(cash / (Decimal("1") + fee_rate))


def intended_notional(
    cash: Decimal,
    fee_rate: Decimal,
    allocated_capital: Decimal,
    max_position_size: Decimal,
) -> Decimal:
    affordable = affordable_notional(cash, fee_rate)
    return quantize_money(min(affordable, allocated_capital, max_position_size))


def is_dust(notional: Decimal) -> bool:
    return notional <= DUST_NOTIONAL


def parse_decimal(value: str) -> Decimal:
    return d(value)
