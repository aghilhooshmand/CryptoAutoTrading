"""Unbound BUY must not re-check Portfolio available."""

from decimal import Decimal

from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def test_unbound_buy_ignores_portfolio_available():
    """Portfolio available is create/start only; Risk has no available field on BUY."""
    rm = RiskManager()
    ctx = RiskContext(
        position_side="flat",
        cash=Decimal("100"),
        qty=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        start_equity=Decimal("100"),
        target_net_profit_amount=Decimal("50"),
        max_session_loss_amount=Decimal("50"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("50"),
        mark_safe=True,
        portfolio_context_enabled=True,
        allocated_capital=Decimal("100"),
        max_position_size=Decimal("100"),
        # No allocation_id → unbound; no portfolio available check.
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.approved
    assert dec.reason_code is None
