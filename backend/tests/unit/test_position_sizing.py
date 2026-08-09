"""Position sizing tests."""

from decimal import Decimal

from app.simulation.position_sizing import intended_notional, is_dust


def test_intended_capped_by_allocated():
    n = intended_notional(
        cash=Decimal("10000"),
        fee_rate=Decimal("0.001"),
        allocated_capital=Decimal("500"),
        max_position_size=Decimal("500"),
    )
    assert n == Decimal("500")


def test_intended_capped_by_cash_after_fee():
    n = intended_notional(
        cash=Decimal("100"),
        fee_rate=Decimal("0.001"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
    )
    assert n < Decimal("100")
    assert n == Decimal("99.90009990")


def test_dust():
    assert is_dust(Decimal("0"))
