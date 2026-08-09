"""Risk manager for long-only simulation bounds."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.simulation.accounting import liquidation_equity, session_net_pnl
from app.simulation.strategy.base import SignalSide, StrategySignal

# Consecutive unsafe safe-quote failures before unrecoverable stop (analyze U1).
UNSAFE_QUOTE_LIMIT = 3


@dataclass
class RiskDecision:
    approved: bool
    reason_code: str | None = None
    reason_message: str | None = None
    trigger_stop: str | None = None


@dataclass
class RiskContext:
    position_side: str
    cash: Decimal
    qty: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    start_equity: Decimal
    target_net_profit_amount: Decimal
    max_session_loss_amount: Decimal
    strategy_fill_count: int
    max_trades: int
    mark_price: Decimal | None
    mark_safe: bool
    emergency: bool = False


class RiskManager:
    def review(self, signal: StrategySignal, ctx: RiskContext) -> RiskDecision:
        if ctx.emergency:
            return RiskDecision(False, "emergency_stop_active", "Emergency stop active", "emergency")
        if signal.side == SignalSide.HOLD:
            return RiskDecision(True)

        if not ctx.mark_safe or ctx.mark_price is None:
            return RiskDecision(
                False,
                "invalid_or_stale_market_data",
                "Mark price unsafe or missing",
            )

        if ctx.strategy_fill_count >= ctx.max_trades:
            return RiskDecision(
                False,
                "maximum_trades_reached",
                "Max strategy fills reached",
                "max_trades",
            )

        liq = liquidation_equity(
            ctx.cash,
            ctx.qty,
            ctx.mark_price,
            ctx.position_side,
            ctx.fee_rate,
            ctx.slippage_rate,
        )
        net = session_net_pnl(liq, ctx.start_equity)
        if net is not None:
            if net >= ctx.target_net_profit_amount:
                return RiskDecision(
                    False,
                    "profit_target_already_reached",
                    "Profit target reached",
                    "profit_target",
                )
            if net <= -ctx.max_session_loss_amount:
                return RiskDecision(
                    False,
                    "maximum_loss_already_reached",
                    "Max session loss reached",
                    "max_loss",
                )

        if signal.side == SignalSide.BUY and ctx.position_side != "flat":
            return RiskDecision(False, "conflicting_position_state", "BUY only from flat")
        if signal.side == SignalSide.SELL and ctx.position_side != "long":
            return RiskDecision(False, "conflicting_position_state", "SELL only while long")

        return RiskDecision(True)
