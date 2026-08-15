"""Shared fill economics and rejection sizing (Feature 012).

Consumes caller-supplied ``reference_price`` only — does not fetch candles or
quotes, and does not select next-open vs live mark.
"""

from __future__ import annotations

from decimal import Decimal

from app.execution.port import ExecutionIntent, FillResult
from app.simulation.accounting import buy_fill, qty_from_notional, sell_fill
from app.simulation.money import quantize_money
from app.simulation.position_sizing import intended_notional, is_dust


def execute_fill(intent: ExecutionIntent) -> FillResult:
    """Apply shared BUY/SELL sizing and reject codes to a fully populated intent."""
    if intent.side == "BUY":
        return _buy(intent)
    if intent.side == "SELL":
        return _sell(intent)
    return FillResult(False, "invalid_side", f"Unsupported side {intent.side}")


def _buy(intent: ExecutionIntent) -> FillResult:
    if intent.position_side != "flat":
        return FillResult(False, "conflicting_position_state", "BUY only from flat")
    target = intended_notional(
        intent.cash,
        intent.fee_rate,
        intent.allocated_capital,
        intent.max_position_size,
    )
    if is_dust(target):
        return FillResult(False, "insufficient_balance", "Intended notional is dust or zero")
    provisional = buy_fill(Decimal("1"), intent.reference_price, intent.fee_rate, intent.slippage_rate)
    qty = qty_from_notional(target, provisional.fill_price)
    if qty <= 0:
        return FillResult(False, "insufficient_balance", "Quantity rounds to zero")
    fill = buy_fill(qty, intent.reference_price, intent.fee_rate, intent.slippage_rate)
    if quantize_money(intent.cash + fill.cash_delta) < 0:
        return FillResult(False, "insufficient_balance", "Cash cannot cover fill + fee")
    return FillResult(True, qty=qty, fill=fill)


def _sell(intent: ExecutionIntent) -> FillResult:
    if intent.position_side != "long" or intent.position_qty <= 0:
        return FillResult(False, "conflicting_position_state", "SELL only while long")
    fill = sell_fill(
        intent.position_qty,
        intent.reference_price,
        intent.fee_rate,
        intent.slippage_rate,
    )
    return FillResult(True, qty=intent.position_qty, fill=fill)
