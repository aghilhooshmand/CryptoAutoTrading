"""Execution engine port and simulation-only implementation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.simulation.accounting import FillQuote, buy_fill, qty_from_notional, sell_fill
from app.simulation.money import quantize_money
from app.simulation.position_sizing import intended_notional, is_dust


@dataclass
class ExecutionIntent:
    side: str  # BUY | SELL
    symbol: str
    reference_price: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    cash: Decimal
    allocated_capital: Decimal
    max_position_size: Decimal
    position_side: str
    position_qty: Decimal
    is_forced_close: bool = False


@dataclass
class FillResult:
    ok: bool
    reason_code: str | None = None
    reason_message: str | None = None
    fill: FillQuote | None = None
    qty: Decimal | None = None


class ExecutionEngine(Protocol):
    def execute(self, intent: ExecutionIntent) -> FillResult: ...


class SimulationExecutionEngine:
    def execute(self, intent: ExecutionIntent) -> FillResult:
        if intent.side == "BUY":
            return self._buy(intent)
        if intent.side == "SELL":
            return self._sell(intent)
        return FillResult(False, "invalid_side", f"Unsupported side {intent.side}")

    def _buy(self, intent: ExecutionIntent) -> FillResult:
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
        # Provisional fill price for qty; recompute with exact qty
        provisional = buy_fill(Decimal("1"), intent.reference_price, intent.fee_rate, intent.slippage_rate)
        qty = qty_from_notional(target, provisional.fill_price)
        if qty <= 0:
            return FillResult(False, "insufficient_balance", "Quantity rounds to zero")
        fill = buy_fill(qty, intent.reference_price, intent.fee_rate, intent.slippage_rate)
        if quantize_money(intent.cash + fill.cash_delta) < 0:
            return FillResult(False, "insufficient_balance", "Cash cannot cover fill + fee")
        return FillResult(True, qty=qty, fill=fill)

    def _sell(self, intent: ExecutionIntent) -> FillResult:
        if intent.position_side != "long" or intent.position_qty <= 0:
            return FillResult(False, "conflicting_position_state", "SELL only while long")
        fill = sell_fill(
            intent.position_qty,
            intent.reference_price,
            intent.fee_rate,
            intent.slippage_rate,
        )
        return FillResult(True, qty=intent.position_qty, fill=fill)
