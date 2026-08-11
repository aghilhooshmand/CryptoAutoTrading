"""HistoricalExecutionAdapter — next-open / end-close fills (Feature 004)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.simulation.accounting import FillQuote, buy_fill, qty_from_notional, sell_fill
from app.simulation.money import quantize_money
from app.simulation.position_sizing import intended_notional, is_dust


@dataclass
class HistoricalFillResult:
    ok: bool
    reason_code: str | None = None
    reason_message: str | None = None
    fill: FillQuote | None = None
    qty: Decimal | None = None


class HistoricalExecutionAdapter:
    """Applies Feature 003 fill math at historically chosen reference prices."""

    def buy(
        self,
        *,
        reference_price: Decimal,
        cash: Decimal,
        fee_rate: Decimal,
        slippage_rate: Decimal,
        allocated_capital: Decimal,
        max_position_size: Decimal,
        position_side: str,
    ) -> HistoricalFillResult:
        if position_side != "flat":
            return HistoricalFillResult(False, "conflicting_position_state", "BUY only from flat")
        target = intended_notional(cash, fee_rate, allocated_capital, max_position_size)
        if is_dust(target):
            return HistoricalFillResult(False, "insufficient_balance", "Intended notional is dust or zero")
        provisional = buy_fill(Decimal("1"), reference_price, fee_rate, slippage_rate)
        qty = qty_from_notional(target, provisional.fill_price)
        if qty <= 0:
            return HistoricalFillResult(False, "insufficient_balance", "Quantity rounds to zero")
        fill = buy_fill(qty, reference_price, fee_rate, slippage_rate)
        if quantize_money(cash + fill.cash_delta) < 0:
            return HistoricalFillResult(False, "insufficient_balance", "Cash cannot cover fill + fee")
        return HistoricalFillResult(True, qty=qty, fill=fill)

    def sell(
        self,
        *,
        reference_price: Decimal,
        fee_rate: Decimal,
        slippage_rate: Decimal,
        position_side: str,
        position_qty: Decimal,
    ) -> HistoricalFillResult:
        if position_side != "long" or position_qty <= 0:
            return HistoricalFillResult(False, "conflicting_position_state", "SELL only while long")
        fill = sell_fill(position_qty, reference_price, fee_rate, slippage_rate)
        return HistoricalFillResult(True, qty=position_qty, fill=fill)
