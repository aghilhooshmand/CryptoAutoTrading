"""Max trades semantics helper checks."""

from decimal import Decimal

from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.strategy.base import SignalSide, StrategySignal


def test_max_trades_triggers_stop_reason():
    rm = RiskManager()
    ctx = RiskContext(
        position_side="flat",
        cash=Decimal("100"),
        qty=Decimal("0"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        start_equity=Decimal("100"),
        target_net_profit_amount=Decimal("50"),
        max_session_loss_amount=Decimal("50"),
        strategy_fill_count=5,
        max_trades=5,
        mark_price=Decimal("100"),
        mark_safe=True,
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.trigger_stop == "max_trades"
