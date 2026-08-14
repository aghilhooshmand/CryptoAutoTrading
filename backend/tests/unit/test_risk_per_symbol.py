"""Per-symbol weight cap Risk decisions."""

from decimal import Decimal

from app.simulation.control.risk import HoldingValueView, RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def _ctx(**over) -> RiskContext:
    data = dict(
        position_side="flat",
        cash=Decimal("400"),
        qty=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        start_equity=Decimal("400"),
        target_net_profit_amount=Decimal("1000"),
        max_session_loss_amount=Decimal("1000"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("100"),
        mark_safe=True,
        portfolio_context_enabled=True,
        allocated_capital=Decimal("400"),
        max_position_size=Decimal("400"),
        per_symbol_max_weight=Decimal("0.2"),
        trade_asset="btc",
        portfolio_equity_complete=True,
        portfolio_current_equity=Decimal("1000"),
        holdings=[HoldingValueView(asset="btc", quantity=Decimal("0"), market_value=Decimal("0"))],
    )
    data.update(over)
    return RiskContext(**data)


def test_projected_weight_breach_rejects():
    rm = RiskManager()
    # intended notional ~400 → weight 0.4 > 0.2
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), _ctx())
    assert not dec.approved
    assert dec.reason_code == "per_symbol_exposure_exceeded"


def test_missing_equity_fail_closed():
    rm = RiskManager()
    ctx = _ctx(portfolio_equity_complete=False, portfolio_current_equity=None)
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "per_symbol_exposure_exceeded"


def test_usdt_trade_asset_uncapped():
    rm = RiskManager()
    ctx = _ctx(trade_asset="usdt", per_symbol_max_weight=Decimal("0.0001"))
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.approved


def test_unset_cap_allows():
    rm = RiskManager()
    ctx = _ctx(per_symbol_max_weight=None)
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert dec.approved
