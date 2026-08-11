"""Decimal helpers and documented simulation cost defaults."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

DEFAULT_FEE_RATE = Decimal("0.002")  # 0.20% — XT Spot VIP0 base maker/taker
DEFAULT_SLIPPAGE_RATE = Decimal("0.0005")  # 0.05% adverse-fill model (not XT schedule)
# Reject BUY when intended notional rounds below this quote-currency floor.
DUST_NOTIONAL = Decimal("0.00000001")

QUANTIZE_MONEY = Decimal("0.00000001")


def d(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(QUANTIZE_MONEY, rounding=ROUND_HALF_UP)


def as_str(value: Decimal) -> str:
    q = quantize_money(value)
    text = format(q, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
