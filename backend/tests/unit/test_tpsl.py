"""Unit tests for Feature 025 TP/SL helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.execution.tpsl import (
    REASON_STOP_LOSS,
    REASON_TAKE_PROFIT,
    derive_levels,
    evaluate_triggers,
    validate_percents,
)


def test_derive_levels_long():
    tp, sl = derive_levels(Decimal("100"), Decimal("0.02"), Decimal("0.01"))
    assert tp == Decimal("102")
    assert sl == Decimal("99")


def test_derive_levels_disabled_sides():
    tp, sl = derive_levels(Decimal("100"), Decimal("0.05"), None)
    assert tp == Decimal("105")
    assert sl is None
    tp2, sl2 = derive_levels(Decimal("100"), None, Decimal("0.1"))
    assert tp2 is None
    assert sl2 == Decimal("90")
    assert derive_levels(Decimal("50"), None, None) == (None, None)


def test_entry_bar_skip():
    reason = evaluate_triggers(
        candle_open_time=1000,
        high=Decimal("200"),
        low=Decimal("1"),
        entry_fill_candle_open_time=1000,
        tp_price=Decimal("110"),
        sl_price=Decimal("90"),
    )
    assert reason is None


def test_sl_wins_when_both_touched():
    reason = evaluate_triggers(
        candle_open_time=2000,
        high=Decimal("120"),
        low=Decimal("80"),
        entry_fill_candle_open_time=1000,
        tp_price=Decimal("110"),
        sl_price=Decimal("90"),
    )
    assert reason == REASON_STOP_LOSS


def test_take_profit_only():
    reason = evaluate_triggers(
        candle_open_time=2000,
        high=Decimal("120"),
        low=Decimal("100"),
        entry_fill_candle_open_time=1000,
        tp_price=Decimal("110"),
        sl_price=Decimal("90"),
    )
    assert reason == REASON_TAKE_PROFIT


def test_neither_side_triggered():
    assert (
        evaluate_triggers(
            candle_open_time=2000,
            high=Decimal("105"),
            low=Decimal("95"),
            entry_fill_candle_open_time=1000,
            tp_price=Decimal("110"),
            sl_price=Decimal("90"),
        )
        is None
    )


def test_disabled_levels_never_trigger():
    assert (
        evaluate_triggers(
            candle_open_time=2000,
            high=Decimal("999"),
            low=Decimal("1"),
            entry_fill_candle_open_time=1000,
            tp_price=None,
            sl_price=None,
        )
        is None
    )


def test_validate_percents_ok_and_disabled():
    assert validate_percents(None, None) == (None, None)
    assert validate_percents("", "") == (None, None)
    tp, sl = validate_percents("0.02", "0.01")
    assert tp == Decimal("0.02")
    assert sl == Decimal("0.01")


@pytest.mark.parametrize(
    "tp,sl",
    [
        ("0", "0.01"),
        ("-0.1", None),
        ("0.02", "0"),
        ("0.02", "1"),
        ("0.02", "1.5"),
        ("not-a-number", None),
    ],
)
def test_validate_percents_invalid(tp, sl):
    with pytest.raises(ValueError):
        validate_percents(tp, sl)
