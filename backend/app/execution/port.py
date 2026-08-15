"""Shared execution types and ExecutionEngine protocol (Feature 012)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.simulation.accounting import FillQuote


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
