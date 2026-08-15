"""Historical execution adapter (Feature 012)."""

from __future__ import annotations

from decimal import Decimal

from app.execution.economics import execute_fill
from app.execution.port import ExecutionIntent, FillResult


class HistoricalExecutionAdapter:
    """Thin Historical adapter — next-open / flatten refs are caller-supplied."""

    def execute(self, intent: ExecutionIntent) -> FillResult:
        return execute_fill(intent)

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
        symbol: str = "",
    ) -> FillResult:
        return self.execute(
            ExecutionIntent(
                side="BUY",
                symbol=symbol,
                reference_price=reference_price,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
                cash=cash,
                allocated_capital=allocated_capital,
                max_position_size=max_position_size,
                position_side=position_side,
                position_qty=Decimal("0"),
            )
        )

    def sell(
        self,
        *,
        reference_price: Decimal,
        fee_rate: Decimal,
        slippage_rate: Decimal,
        position_side: str,
        position_qty: Decimal,
        cash: Decimal = Decimal("0"),
        allocated_capital: Decimal = Decimal("0"),
        max_position_size: Decimal = Decimal("0"),
        symbol: str = "",
        is_forced_close: bool = False,
    ) -> FillResult:
        return self.execute(
            ExecutionIntent(
                side="SELL",
                symbol=symbol,
                reference_price=reference_price,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
                cash=cash,
                allocated_capital=allocated_capital,
                max_position_size=max_position_size,
                position_side=position_side,
                position_qty=position_qty,
                is_forced_close=is_forced_close,
            )
        )


# Migration alias — same fields as FillResult
HistoricalFillResult = FillResult
