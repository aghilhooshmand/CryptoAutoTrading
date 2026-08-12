"""Unit tests for strategy ParamDef coercion (integer + decimal_string)."""

from __future__ import annotations

import pytest

from app.strategy.params import ParamDef, StrategyParamError, validate_params

_STDDEV = ParamDef(
    name="stdDev",
    type="decimal_string",
    label="Std deviations",
    default="2.0",
    minimum=0,
    exclusive_minimum=True,
)

_PERIOD = ParamDef(
    name="period",
    type="integer",
    label="Period",
    default=20,
    minimum=2,
)


def test_decimal_string_preserves_submitted_spelling() -> None:
    out = validate_params([_STDDEV], {"stdDev": "2.0"})
    assert out["stdDev"] == "2.0"
    out = validate_params([_STDDEV], {"stdDev": "1.5"})
    assert out["stdDev"] == "1.5"
    out = validate_params([_STDDEV], {"stdDev": "0.5"})
    assert out["stdDev"] == "0.5"


def test_decimal_string_default_applied() -> None:
    out = validate_params([_STDDEV], None)
    assert out["stdDev"] == "2.0"


def test_decimal_string_rejects_malformed() -> None:
    with pytest.raises(StrategyParamError) as ei:
        validate_params([_STDDEV], {"stdDev": "abc"})
    assert ei.value.code == "invalid_strategy_params"
    assert "decimal string" in ei.value.message


def test_decimal_string_exclusive_minimum_rejects_zero_and_negative() -> None:
    with pytest.raises(StrategyParamError) as ei0:
        validate_params([_STDDEV], {"stdDev": "0"})
    assert ei0.value.code == "invalid_strategy_params"
    assert "must be > 0" in ei0.value.message

    with pytest.raises(StrategyParamError) as ei_neg:
        validate_params([_STDDEV], {"stdDev": "-0.1"})
    assert ei_neg.value.code == "invalid_strategy_params"
    assert "must be > 0" in ei_neg.value.message


def test_decimal_string_accepts_json_number_as_decimal_string() -> None:
    out = validate_params([_STDDEV], {"stdDev": 2.5})
    assert out["stdDev"] == "2.5"


def test_integer_bounds_still_work() -> None:
    out = validate_params([_PERIOD], {"period": 10})
    assert out["period"] == 10
    with pytest.raises(StrategyParamError):
        validate_params([_PERIOD], {"period": 1})
