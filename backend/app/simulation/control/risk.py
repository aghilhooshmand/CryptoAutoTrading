"""Risk manager for long-only simulation bounds (Feature 003 + 010)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.simulation.accounting import liquidation_equity, session_net_pnl
from app.simulation.control import reasons as R
from app.simulation.position_sizing import intended_notional, is_dust
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
class HoldingValueView:
    asset: str
    quantity: Decimal
    market_value: Decimal | None  # None = unvalued / missing


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
    # Feature 010 — portfolio context (disabled for Backtest/Comparison).
    portfolio_context_enabled: bool = False
    allocated_capital: Decimal | None = None
    max_position_size: Decimal | None = None
    allocation_id: str | None = None
    allocation_reserved: Decimal | None = None
    allocation_deployed: Decimal | None = None
    portfolio_max_loss_amount: Decimal | None = None
    portfolio_loss_baseline_kind: str | None = None  # equity | quote_cash
    portfolio_loss_baseline_value: Decimal | None = None
    portfolio_equity_complete: bool | None = None
    portfolio_current_equity: Decimal | None = None
    portfolio_quote_cash: Decimal | None = None
    per_symbol_max_weight: Decimal | None = None
    trade_asset: str | None = None  # base asset e.g. btc
    holdings: list[HoldingValueView] = field(default_factory=list)


def _reject(code: str, *, trigger_stop: str | None = None, message: str | None = None) -> RiskDecision:
    return RiskDecision(
        False,
        code,
        message if message is not None else R.message_for(code),
        trigger_stop,
    )


def _current_portfolio_metric(ctx: RiskContext) -> Decimal | None:
    kind = ctx.portfolio_loss_baseline_kind
    if kind == "equity":
        if ctx.portfolio_equity_complete is not True or ctx.portfolio_current_equity is None:
            return None
        return ctx.portfolio_current_equity
    if kind == "quote_cash":
        if ctx.portfolio_quote_cash is None:
            return None
        return ctx.portfolio_quote_cash
    return None


def _portfolio_max_loss_decision(ctx: RiskContext, *, is_buy: bool) -> RiskDecision | None:
    if not ctx.portfolio_context_enabled:
        return None
    if ctx.portfolio_max_loss_amount is None or ctx.portfolio_loss_baseline_value is None:
        return None
    if ctx.portfolio_loss_baseline_kind not in ("equity", "quote_cash"):
        return None
    current = _current_portfolio_metric(ctx)
    if current is None:
        if is_buy:
            return _reject(R.PORTFOLIO_MAX_LOSS_UNCOMPUTABLE)
        return None
    loss = ctx.portfolio_loss_baseline_value - current
    if loss >= ctx.portfolio_max_loss_amount:
        return _reject(R.PORTFOLIO_MAX_LOSS, trigger_stop=R.STOP_PORTFOLIO_MAX_LOSS)
    return None


def _allocation_remaining_ok(ctx: RiskContext, notional: Decimal) -> bool:
    if ctx.allocation_id is None:
        return True
    if ctx.allocation_reserved is None:
        return False  # bound but reserved unknown — fail closed
    deployed = ctx.allocation_deployed or Decimal("0")
    remaining = ctx.allocation_reserved - deployed
    return notional <= remaining


def _projected_post_buy_weight(ctx: RiskContext, notional: Decimal) -> Decimal | None:
    """Return projected weight of trade_asset after BUY, or None if uncomputable."""
    if ctx.per_symbol_max_weight is None or ctx.trade_asset is None:
        return None
    if ctx.mark_price is None or not ctx.mark_safe:
        return None
    if ctx.portfolio_equity_complete is not True or ctx.portfolio_current_equity is None:
        return None
    if ctx.portfolio_current_equity <= 0:
        return None

    asset = ctx.trade_asset.lower()
    if asset == "usdt":
        return Decimal("0")  # quote uncapped — caller should skip

    existing_value = Decimal("0")
    for h in ctx.holdings:
        if h.asset.lower() != asset:
            continue
        if h.market_value is None:
            return None
        existing_value = h.market_value
        break

    # BUY spends USDT notional and adds ~notional of asset value at mark (approx).
    projected_asset = existing_value + notional
    projected_equity = ctx.portfolio_current_equity  # USDT down, asset up ≈ net flat at fill
    # More precisely: equity shifts by (asset mark value gained − USDT spent).
    # At intended notional ≈ market value of fill, equity ~ unchanged.
    if projected_equity <= 0:
        return None
    return projected_asset / projected_equity


class RiskManager:
    def review(self, signal: StrategySignal, ctx: RiskContext) -> RiskDecision:
        # 1. Emergency
        if ctx.emergency:
            return _reject(R.EMERGENCY_STOP_ACTIVE, trigger_stop=R.STOP_EMERGENCY)

        if signal.side == SignalSide.HOLD:
            return RiskDecision(True)

        is_buy = signal.side == SignalSide.BUY

        # 3. Unsafe / missing mark
        if not ctx.mark_safe or ctx.mark_price is None:
            return _reject(R.INVALID_OR_STALE_MARKET_DATA)

        # 4. Portfolio max-loss (uncomputable BUY block or stop)
        pml = _portfolio_max_loss_decision(ctx, is_buy=is_buy)
        if pml is not None:
            return pml

        # 5. Session max trades / profit / loss
        if ctx.strategy_fill_count >= ctx.max_trades:
            return _reject(R.MAXIMUM_TRADES_REACHED, trigger_stop=R.STOP_MAX_TRADES)

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
                return _reject(R.PROFIT_TARGET_ALREADY_REACHED, trigger_stop=R.STOP_PROFIT_TARGET)
            if net <= -ctx.max_session_loss_amount:
                return _reject(R.MAXIMUM_LOSS_ALREADY_REACHED, trigger_stop=R.STOP_MAX_LOSS)

        # 6. Conflicting position
        if signal.side == SignalSide.BUY and ctx.position_side != "flat":
            return _reject(
                R.CONFLICTING_POSITION_STATE,
                message="BUY only from flat",
            )
        if signal.side == SignalSide.SELL and ctx.position_side != "long":
            return _reject(
                R.CONFLICTING_POSITION_STATE,
                message="SELL only while long",
            )

        # Portfolio BUY gates (7–9) then session sizing (catalog §9) — only when enabled and BUY
        if ctx.portfolio_context_enabled and is_buy:
            notional: Decimal | None = None
            if ctx.allocated_capital is not None and ctx.max_position_size is not None:
                notional = intended_notional(
                    ctx.cash,
                    ctx.fee_rate,
                    ctx.allocated_capital,
                    ctx.max_position_size,
                )

            # 7. Allocation remaining (bound only)
            if ctx.allocation_id is not None:
                if ctx.allocation_reserved is None:
                    return _reject(R.ALLOCATION_EXPOSURE_EXCEEDED)
                if notional is not None and not _allocation_remaining_ok(ctx, notional):
                    return _reject(R.ALLOCATION_EXPOSURE_EXCEEDED)

            # 8. Per-symbol weight (USDT uncapped)
            if (
                ctx.per_symbol_max_weight is not None
                and ctx.trade_asset
                and ctx.trade_asset.lower() != "usdt"
            ):
                if notional is None:
                    return _reject(R.PER_SYMBOL_EXPOSURE_EXCEEDED)
                weight = _projected_post_buy_weight(ctx, notional)
                if weight is None or weight > ctx.per_symbol_max_weight:
                    return _reject(R.PER_SYMBOL_EXPOSURE_EXCEEDED)

            # 9. Session sizing / dust
            if notional is None or is_dust(notional):
                return _reject(R.INSUFFICIENT_BALANCE)

        return RiskDecision(True)
