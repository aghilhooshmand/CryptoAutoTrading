"""Risk reject and forced-close unit tests."""

from decimal import Decimal

from app.simulation.control.risk import RiskContext, RiskManager
from app.simulation.execution.port import ExecutionIntent, SimulationExecutionEngine
from app.simulation.strategy.base import SignalSide, StrategySignal


def test_reject_buy_while_long():
    rm = RiskManager()
    ctx = RiskContext(
        position_side="long",
        cash=Decimal("0"),
        qty=Decimal("1"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        start_equity=Decimal("100"),
        target_net_profit_amount=Decimal("10"),
        max_session_loss_amount=Decimal("10"),
        strategy_fill_count=0,
        max_trades=10,
        mark_price=Decimal("100"),
        mark_safe=True,
    )
    dec = rm.review(StrategySignal(SignalSide.BUY, 1, None, None), ctx)
    assert not dec.approved
    assert dec.reason_code == "conflicting_position_state"


def test_forced_sell_full_close():
    eng = SimulationExecutionEngine()
    intent = ExecutionIntent(
        side="SELL",
        symbol="btc_usdt",
        reference_price=Decimal("100"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        cash=Decimal("0"),
        allocated_capital=Decimal("100"),
        max_position_size=Decimal("100"),
        position_side="long",
        position_qty=Decimal("1"),
        is_forced_close=True,
    )
    res = eng.execute(intent)
    assert res.ok
    assert res.qty == Decimal("1")
    assert res.fill is not None
