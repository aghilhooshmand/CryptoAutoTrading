"""Portfolio max-loss Risk decisions."""

from decimal import Decimal

from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def _ctx(**over) -> RiskContext:
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
        portfolio_max_loss_amount=Decimal("50"),
        portfolio_loss_baseline_kind="equity",
        portfolio_loss_baseline_value=Decimal("1000"),
        portfolio_equity_complete=True,
        portfolio_current_equity=Decimal("1000"),
    )
    data.update(over)
    return RiskContext(**data)


def test_reached_triggers_stop():
    rm = RiskManager()
    ctx = _ctx(portfolio_current_equity=Decimal("940"))
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "portfolio_max_loss"
    assert dec.trigger_stop == "portfolio_max_loss"


def test_uncomputable_rejects_buy_without_stop():
    rm = RiskManager()
    ctx = _ctx(portfolio_equity_complete=False, portfolio_current_equity=None)
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "portfolio_max_loss_uncomputable"
    assert dec.trigger_stop is None


def test_uncomputable_allows_sell():
    rm = RiskManager()
    ctx = _ctx(
        position_side="long",
        qty=Decimal("1"),
        cash=Decimal("900"),
        start_equity=Decimal("1000"),
        max_session_loss_amount=Decimal("500"),
        portfolio_equity_complete=False,
        portfolio_current_equity=None,
    )
    dec = rm.review(StrategySignal(SignalSide.SELL, 1, None, None), ctx)
    assert dec.approved


def test_quote_cash_baseline():
    rm = RiskManager()
    ctx = _ctx(
        portfolio_loss_baseline_kind="quote_cash",
        portfolio_loss_baseline_value=Decimal("1000"),
        portfolio_quote_cash=Decimal("900"),
        portfolio_max_loss_amount=Decimal("50"),
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "portfolio_max_loss"


def test_disabled_portfolio_context_skips_max_loss():
    rm = RiskManager()
    ctx = _ctx(portfolio_context_enabled=False, portfolio_current_equity=Decimal("0"))
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.approved
