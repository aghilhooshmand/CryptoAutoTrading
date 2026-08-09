"""Forced close accounting: hyp costs not double-applied (fill once)."""

from decimal import Decimal

from app.simulation.accounting import liquidation_equity, sell_fill


def test_forced_close_cash_equals_precomputed_liquidation():
    cash = Decimal("10")
    qty = Decimal("1")
    mark = Decimal("100")
    fee = Decimal("0.001")
    slip = Decimal("0.0005")
    liq = liquidation_equity(cash, qty, mark, "long", fee, slip)
    fill = sell_fill(qty, mark, fee, slip)
    after = cash + fill.cash_delta
    assert liq == after
