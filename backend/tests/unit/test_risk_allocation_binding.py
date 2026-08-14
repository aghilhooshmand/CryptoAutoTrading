"""Allocation remaining gate on bound BUY."""

from decimal import Decimal

from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def test_bound_buy_rejects_when_notional_exceeds_remaining():
    rm = RiskManager()
    ctx = RiskContext(
        position_side="flat",
        cash=Decimal("500"),
        qty=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        start_equity=Decimal("500"),
        target_net_profit_amount=Decimal("50"),
        max_session_loss_amount=Decimal("50"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("100"),
        mark_safe=True,
        portfolio_context_enabled=True,
        allocated_capital=Decimal("500"),
        max_position_size=Decimal("500"),
        allocation_id="alloc-1",
        allocation_reserved=Decimal("200"),
        allocation_deployed=Decimal("150"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "allocation_exposure_exceeded"


def test_unbound_has_no_allocation_gate():
    rm = RiskManager()
    ctx = RiskContext(
        position_side="flat",
        cash=Decimal("500"),
        qty=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        start_equity=Decimal("500"),
        target_net_profit_amount=Decimal("50"),
        max_session_loss_amount=Decimal("50"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("100"),
        mark_safe=True,
        portfolio_context_enabled=True,
        allocated_capital=Decimal("500"),
        max_position_size=Decimal("500"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.approved
