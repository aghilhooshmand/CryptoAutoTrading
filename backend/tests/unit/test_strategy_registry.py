"""Unit tests for strategy registry resolve / validate."""

from __future__ import annotations

import pytest

from app.strategy.dual_ema import FAST_LT_SLOW_MESSAGE
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, validate_and_materialize


def test_resolve_canonical_dual_ema():
    cid, params, inst = validate_and_materialize("dual_ema", None)
    assert cid == "dual_ema"
    assert params == {"fastPeriod": 9, "slowPeriod": 21}
    assert inst.min_history_candles() == 21


def test_alias_resolves_and_persists_canonical():
    cid, params, _ = validate_and_materialize("dual_ema_9_21", None)
    assert cid == "dual_ema"
    assert params["fastPeriod"] == 9
    assert params["slowPeriod"] == 21


def test_omit_strategy_id_rejected():
    with pytest.raises(StrategyParamError) as ei:
        validate_and_materialize(None, None)
    assert ei.value.code == "missing_strategy"


def test_unknown_strategy_rejected():
    with pytest.raises(UnknownStrategyError):
        validate_and_materialize("no_such_strategy", None)


def test_fast_not_less_than_slow_message():
    with pytest.raises(StrategyParamError) as ei:
        validate_and_materialize("dual_ema", {"fastPeriod": 21, "slowPeriod": 9})
    assert ei.value.message == FAST_LT_SLOW_MESSAGE


def test_custom_valid_periods():
    cid, params, inst = validate_and_materialize(
        "dual_ema", {"fastPeriod": 12, "slowPeriod": 26}
    )
    assert cid == "dual_ema"
    assert params == {"fastPeriod": 12, "slowPeriod": 26}
    assert inst.min_history_candles() == 26
