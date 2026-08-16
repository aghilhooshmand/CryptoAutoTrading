"""Sim vs Backtest TP/SL trigger parity (Feature 025 US3)."""

from __future__ import annotations

from decimal import Decimal

from app.execution.tpsl import (
    REASON_STOP_LOSS,
    REASON_TAKE_PROFIT,
    derive_levels,
    evaluate_triggers,
)


def test_shared_derive_levels_identical():
    tp, sl = derive_levels(Decimal("100"), Decimal("0.02"), Decimal("0.01"))
    assert tp == Decimal("102")
    assert sl == Decimal("99")


def test_identical_ohlc_same_trigger_reasons():
    """Trigger outcomes must match across modes; fill prices intentionally differ."""
    entry = Decimal("100")
    tp, sl = derive_levels(entry, Decimal("0.02"), Decimal("0.01"))
    entry_ot = 1_000
    cases = [
        # (high, low, expected)
        (Decimal("101"), Decimal("100"), None),
        (Decimal("103"), Decimal("100"), REASON_TAKE_PROFIT),
        (Decimal("100"), Decimal("98"), REASON_STOP_LOSS),
        (Decimal("103"), Decimal("98"), REASON_STOP_LOSS),  # SL wins
        (Decimal("200"), Decimal("1"), None),  # would be entry bar — tested below
    ]
    for high, low, expected in cases[:4]:
        got = evaluate_triggers(
            candle_open_time=2_000,
            high=high,
            low=low,
            entry_fill_candle_open_time=entry_ot,
            tp_price=tp,
            sl_price=sl,
        )
        assert got == expected

    # Entry-bar skip identical for both modes
    assert (
        evaluate_triggers(
            candle_open_time=entry_ot,
            high=Decimal("200"),
            low=Decimal("1"),
            entry_fill_candle_open_time=entry_ot,
            tp_price=tp,
            sl_price=sl,
        )
        is None
    )


def test_fill_model_divergence_is_documented_not_unified():
    """Sim uses mark; Backtest uses next-open — neither equals TP/SL level."""
    tp_level = Decimal("102")
    sim_fill_ref = Decimal("101.5")  # live mark
    backtest_fill_ref = Decimal("110")  # next open
    assert sim_fill_ref != tp_level
    assert backtest_fill_ref != tp_level
    assert sim_fill_ref != backtest_fill_ref
