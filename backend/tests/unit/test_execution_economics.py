"""Dual-oracle parity: shared economics vs frozen pre-012 Simulation/Historical logic."""

from __future__ import annotations

from decimal import Decimal

from app.execution.economics import execute_fill
from app.execution.historical import HistoricalExecutionAdapter
from app.execution.port import ExecutionIntent, FillResult
from app.execution.simulation import SimulationExecutionEngine
from app.simulation.accounting import buy_fill, qty_from_notional, sell_fill
from app.simulation.money import quantize_money
from app.simulation.position_sizing import intended_notional, is_dust

FEE = Decimal("0.001")
SLIP = Decimal("0.0005")
REF = Decimal("100")


def _legacy_sim_execute(intent: ExecutionIntent) -> FillResult:
    """Frozen copy of pre-012 SimulationExecutionEngine (oracle)."""
    if intent.side == "BUY":
        if intent.position_side != "flat":
            return FillResult(False, "conflicting_position_state", "BUY only from flat")
        target = intended_notional(
            intent.cash, intent.fee_rate, intent.allocated_capital, intent.max_position_size
        )
        if is_dust(target):
            return FillResult(False, "insufficient_balance", "Intended notional is dust or zero")
        provisional = buy_fill(Decimal("1"), intent.reference_price, intent.fee_rate, intent.slippage_rate)
        qty = qty_from_notional(target, provisional.fill_price)
        if qty <= 0:
            return FillResult(False, "insufficient_balance", "Quantity rounds to zero")
        fill = buy_fill(qty, intent.reference_price, intent.fee_rate, intent.slippage_rate)
        if quantize_money(intent.cash + fill.cash_delta) < 0:
            return FillResult(False, "insufficient_balance", "Cash cannot cover fill + fee")
        return FillResult(True, qty=qty, fill=fill)
    if intent.side == "SELL":
        if intent.position_side != "long" or intent.position_qty <= 0:
            return FillResult(False, "conflicting_position_state", "SELL only while long")
        fill = sell_fill(
            intent.position_qty, intent.reference_price, intent.fee_rate, intent.slippage_rate
        )
        return FillResult(True, qty=intent.position_qty, fill=fill)
    return FillResult(False, "invalid_side", f"Unsupported side {intent.side}")


def _legacy_hist_buy(**kwargs) -> FillResult:
    """Frozen copy of pre-012 HistoricalExecutionAdapter.buy (oracle)."""
    position_side = kwargs["position_side"]
    cash = kwargs["cash"]
    fee_rate = kwargs["fee_rate"]
    slippage_rate = kwargs["slippage_rate"]
    allocated_capital = kwargs["allocated_capital"]
    max_position_size = kwargs["max_position_size"]
    reference_price = kwargs["reference_price"]
    if position_side != "flat":
        return FillResult(False, "conflicting_position_state", "BUY only from flat")
    target = intended_notional(cash, fee_rate, allocated_capital, max_position_size)
    if is_dust(target):
        return FillResult(False, "insufficient_balance", "Intended notional is dust or zero")
    provisional = buy_fill(Decimal("1"), reference_price, fee_rate, slippage_rate)
    qty = qty_from_notional(target, provisional.fill_price)
    if qty <= 0:
        return FillResult(False, "insufficient_balance", "Quantity rounds to zero")
    fill = buy_fill(qty, reference_price, fee_rate, slippage_rate)
    if quantize_money(cash + fill.cash_delta) < 0:
        return FillResult(False, "insufficient_balance", "Cash cannot cover fill + fee")
    return FillResult(True, qty=qty, fill=fill)


def _legacy_hist_sell(**kwargs) -> FillResult:
    position_side = kwargs["position_side"]
    position_qty = kwargs["position_qty"]
    reference_price = kwargs["reference_price"]
    fee_rate = kwargs["fee_rate"]
    slippage_rate = kwargs["slippage_rate"]
    if position_side != "long" or position_qty <= 0:
        return FillResult(False, "conflicting_position_state", "SELL only while long")
    fill = sell_fill(position_qty, reference_price, fee_rate, slippage_rate)
    return FillResult(True, qty=position_qty, fill=fill)


def _assert_same(a: FillResult, b: FillResult) -> None:
    assert a.ok == b.ok
    assert a.reason_code == b.reason_code
    assert a.qty == b.qty
    if a.fill is None:
        assert b.fill is None
        return
    assert b.fill is not None
    assert a.fill.reference_price == b.fill.reference_price
    assert a.fill.fill_price == b.fill.fill_price
    assert a.fill.notional == b.fill.notional
    assert a.fill.fee == b.fill.fee
    assert a.fill.slippage_cost == b.fill.slippage_cost
    assert a.fill.cash_delta == b.fill.cash_delta


def _buy_intent(**overrides) -> ExecutionIntent:
    base = dict(
        side="BUY",
        symbol="btc_usdt",
        reference_price=REF,
        fee_rate=FEE,
        slippage_rate=SLIP,
        cash=Decimal("1000"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        position_side="flat",
        position_qty=Decimal("0"),
    )
    base.update(overrides)
    return ExecutionIntent(**base)


def _sell_intent(**overrides) -> ExecutionIntent:
    base = dict(
        side="SELL",
        symbol="btc_usdt",
        reference_price=REF,
        fee_rate=FEE,
        slippage_rate=SLIP,
        cash=Decimal("0"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        position_side="long",
        position_qty=Decimal("1"),
    )
    base.update(overrides)
    return ExecutionIntent(**base)


def test_buy_success_matches_legacy_sim_and_hist():
    intent = _buy_intent()
    shared = execute_fill(intent)
    sim_legacy = _legacy_sim_execute(intent)
    hist_legacy = _legacy_hist_buy(
        reference_price=intent.reference_price,
        cash=intent.cash,
        fee_rate=intent.fee_rate,
        slippage_rate=intent.slippage_rate,
        allocated_capital=intent.allocated_capital,
        max_position_size=intent.max_position_size,
        position_side=intent.position_side,
    )
    _assert_same(shared, sim_legacy)
    _assert_same(shared, hist_legacy)
    assert shared.ok
    assert shared.qty is not None and shared.qty > 0
    assert shared.fill is not None
    assert shared.fill.fee > 0
    assert shared.fill.slippage_cost >= 0
    assert shared.fill.cash_delta < 0


def test_sell_success_matches_legacy():
    intent = _sell_intent()
    shared = execute_fill(intent)
    _assert_same(shared, _legacy_sim_execute(intent))
    _assert_same(
        shared,
        _legacy_hist_sell(
            reference_price=intent.reference_price,
            fee_rate=intent.fee_rate,
            slippage_rate=intent.slippage_rate,
            position_side=intent.position_side,
            position_qty=intent.position_qty,
        ),
    )


def test_dust_and_conflict_and_invalid_side():
    dust = execute_fill(_buy_intent(cash=Decimal("0.0000001"), allocated_capital=Decimal("0.0000001"), max_position_size=Decimal("0.0000001")))
    assert dust.ok is False
    assert dust.reason_code == "insufficient_balance"
    _assert_same(dust, _legacy_sim_execute(_buy_intent(cash=Decimal("0.0000001"), allocated_capital=Decimal("0.0000001"), max_position_size=Decimal("0.0000001"))))

    conflict = execute_fill(_buy_intent(position_side="long", position_qty=Decimal("1")))
    assert conflict.reason_code == "conflicting_position_state"

    bad = execute_fill(_buy_intent(side="HOLD"))
    assert bad.reason_code == "invalid_side"


def test_adapters_execute_match_shared_and_each_other():
    sim = SimulationExecutionEngine()
    hist = HistoricalExecutionAdapter()
    for intent in (_buy_intent(), _sell_intent(), _buy_intent(position_side="long", position_qty=Decimal("1"))):
        shared = execute_fill(intent)
        _assert_same(shared, sim.execute(intent))
        _assert_same(shared, hist.execute(intent))


def test_hist_buy_sell_wrappers_call_execute_only():
    hist = HistoricalExecutionAdapter()
    buy = hist.buy(
        reference_price=REF,
        cash=Decimal("1000"),
        fee_rate=FEE,
        slippage_rate=SLIP,
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        position_side="flat",
    )
    _assert_same(buy, execute_fill(_buy_intent()))
    sell = hist.sell(
        reference_price=REF,
        fee_rate=FEE,
        slippage_rate=SLIP,
        position_side="long",
        position_qty=Decimal("1"),
    )
    _assert_same(sell, execute_fill(_sell_intent()))
