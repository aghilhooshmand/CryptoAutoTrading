"""Unit tests for accounting helpers."""

from decimal import Decimal

from app.simulation.accounting import (
    buy_fill,
    liquidation_equity,
    mark_equity,
    sell_fill,
    session_net_pnl,
)


def test_buy_fill_adverse_slippage_and_fee():
    fill = buy_fill(Decimal("1"), Decimal("100"), Decimal("0.001"), Decimal("0.0005"))
    assert fill.fill_price == Decimal("100.05")
    assert fill.fee == Decimal("0.10005")
    assert fill.slippage_cost == Decimal("0.05")
    assert fill.cash_delta < 0


def test_liquidation_equity_worse_than_mark():
    cash = Decimal("0")
    qty = Decimal("1")
    mark = Decimal("100")
    m = mark_equity(cash, qty, mark, "long")
    liq = liquidation_equity(cash, qty, mark, "long", Decimal("0.001"), Decimal("0.0005"))
    assert m == Decimal("100")
    assert liq is not None and liq < m
    # hyp sell at 99.95, fee on notional
    assert session_net_pnl(liq, Decimal("100")) is not None


def test_sell_fill_matches_liquidation_components():
    fill = sell_fill(Decimal("2"), Decimal("50"), Decimal("0.001"), Decimal("0.0005"))
    assert fill.fill_price == Decimal("49.975")
    assert fill.cash_delta == fill.notional - fill.fee
