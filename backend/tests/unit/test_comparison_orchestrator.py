"""Unit tests for comparison orchestrator validation and metrics mapping."""

from __future__ import annotations

import pytest

from app.comparison.metrics import leg_metrics_from_summary
from app.comparison.service import (
    ComparisonError,
    comparison_lock_held,
    validate_create_body,
)


def _body(**over):
    base = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_000_000 + 40 * 3_600_000,
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "legs": [
            {"strategyId": "dual_ema"},
            {"strategyId": "rsi"},
        ],
    }
    base.update(over)
    return base


def test_rejects_one_leg():
    with pytest.raises(ComparisonError) as ei:
        validate_create_body(_body(legs=[{"strategyId": "dual_ema"}]))
    assert ei.value.code == "invalid_comparison"


def test_rejects_six_legs():
    legs = [{"strategyId": "dual_ema"} for _ in range(6)]
    with pytest.raises(ComparisonError) as ei:
        validate_create_body(_body(legs=legs))
    assert ei.value.code == "invalid_comparison"


def test_accepts_two_to_five_legs():
    shared, legs = validate_create_body(_body())
    assert shared["symbol"] == "btc_usdt"
    assert len(legs) == 2
    assert legs[0]["strategy_id"] in ("dual_ema", "dual_ema_9_21") or "dual_ema" in legs[0][
        "strategy_id"
    ]


def test_strictest_min_history_from_legs():
    _, legs = validate_create_body(
        _body(
            legs=[
                {"strategyId": "dual_ema", "strategyParams": {"fastPeriod": 9, "slowPeriod": 21}},
                {"strategyId": "rsi", "strategyParams": {"period": 14, "overbought": 70, "oversold": 30}},
            ]
        )
    )
    strictest = max(int(leg["min_history_candles"]) for leg in legs)
    assert strictest >= 21


def test_duplicate_strategy_ids_allowed():
    _, legs = validate_create_body(
        _body(
            legs=[
                {"strategyId": "rsi", "strategyParams": {"period": 14, "overbought": 70, "oversold": 30}},
                {"strategyId": "rsi", "strategyParams": {"period": 10, "overbought": 65, "oversold": 35}},
            ]
        )
    )
    assert len(legs) == 2
    assert legs[0]["strategy_id"] == legs[1]["strategy_id"]
    assert legs[0]["strategy_params"] != legs[1]["strategy_params"]


def test_invalid_params_reject():
    with pytest.raises(ComparisonError) as ei:
        validate_create_body(
            _body(
                legs=[
                    {"strategyId": "dual_ema"},
                    {
                        "strategyId": "rsi",
                        "strategyParams": {"period": 14, "overbought": 20, "oversold": 80},
                    },
                ]
            )
        )
    assert ei.value.code in ("invalid_strategy_params", "constraint_violation")


def test_fill_count_alias_and_vs_bh():
    metrics = leg_metrics_from_summary(
        {
            "netPnl": "10",
            "returnPct": "0.05",
            "maxDrawdown": "1",
            "maxDrawdownPct": "0.01",
            "winRate": "0.5",
            "roundTripCount": 2,
            "strategyFillCount": 5,
            "totalFees": "0.1",
            "totalSlippage": "0.05",
            "bestTrade": "3",
            "worstTrade": "-1",
            "buyAndHoldReturnPct": "0.02",
        },
        shared_bh_return_pct="0.02",
    )
    assert metrics["fillCount"] == 5
    assert metrics["roundTripCount"] == 2
    assert metrics["vsBuyAndHoldReturnPct"] == "0.03"
    assert metrics["buyAndHoldReturnPct"] == "0.02"


def test_comparison_lock_not_held_by_default():
    assert comparison_lock_held() is False
