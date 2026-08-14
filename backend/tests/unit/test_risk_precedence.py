"""First-fail precedence for Feature 010 RiskManager."""

from decimal import Decimal

from app.simulation.control.risk import HoldingValueView, RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def _base(**over) -> RiskContext:
    data = dict(
        position_side="flat",
        cash=Decimal("1000"),
        qty=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        start_equity=Decimal("1000"),
        target_net_profit_amount=Decimal("100"),
        max_session_loss_amount=Decimal("100"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("100"),
        mark_safe=True,
        portfolio_context_enabled=True,
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
    )
    data.update(over)
    return RiskContext(**data)


def test_emergency_beats_portfolio_max_loss():
    rm = RiskManager()
    ctx = _base(
        emergency=True,
        portfolio_max_loss_amount=Decimal("1"),
        portfolio_loss_baseline_kind="equity",
        portfolio_loss_baseline_value=Decimal("1000"),
        portfolio_equity_complete=True,
        portfolio_current_equity=Decimal("0"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.reason_code == "emergency_stop_active"


def test_stale_mark_beats_allocation():
    rm = RiskManager()
    ctx = _base(
        mark_safe=False,
        allocation_id="a1",
        allocation_reserved=Decimal("1"),
        allocation_deployed=Decimal("0"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.reason_code == "invalid_or_stale_market_data"


def test_portfolio_max_loss_beats_allocation():
    rm = RiskManager()
    ctx = _base(
        portfolio_max_loss_amount=Decimal("10"),
        portfolio_loss_baseline_kind="equity",
        portfolio_loss_baseline_value=Decimal("1000"),
        portfolio_equity_complete=True,
        portfolio_current_equity=Decimal("980"),
        allocation_id="a1",
        allocation_reserved=Decimal("1"),
        allocation_deployed=Decimal("0"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.reason_code == "portfolio_max_loss"
    assert dec.trigger_stop == "portfolio_max_loss"


def test_allocation_beats_per_symbol():
    rm = RiskManager()
    ctx = _base(
        cash=Decimal("500"),
        start_equity=Decimal("500"),
        target_net_profit_amount=Decimal("1000"),
        max_session_loss_amount=Decimal("1000"),
        allocated_capital=Decimal("500"),
        max_position_size=Decimal("500"),
        allocation_id="a1",
        allocation_reserved=Decimal("10"),
        allocation_deployed=Decimal("0"),
        per_symbol_max_weight=Decimal("0.01"),
        trade_asset="btc",
        portfolio_equity_complete=True,
        portfolio_current_equity=Decimal("1000"),
        holdings=[HoldingValueView(asset="btc", quantity=Decimal("0"), market_value=Decimal("0"))],
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.reason_code == "allocation_exposure_exceeded"
