"""Integration: simulation and backtest share strategy resolution via registry."""

from __future__ import annotations

from app.strategy.dual_ema import DualEmaCrossoverStrategy
from app.strategy.rsi import RsiStrategy
from app.strategy.registry import validate_and_materialize


def test_sim_and_backtest_resolve_same_dual_ema_class():
    _, params_a, inst_a = validate_and_materialize("dual_ema", None)
    _, params_b, inst_b = validate_and_materialize("dual_ema_9_21", None)
    assert params_a == params_b == {"fastPeriod": 9, "slowPeriod": 21}
    assert type(inst_a) is DualEmaCrossoverStrategy
    assert type(inst_b) is DualEmaCrossoverStrategy
    assert inst_a.fast == inst_b.fast == 9
    assert inst_a.slow == inst_b.slow == 21


def test_sim_and_backtest_resolve_same_rsi_class():
    _, params_a, inst_a = validate_and_materialize("rsi", None)
    _, params_b, inst_b = validate_and_materialize(
        "rsi",
        {"period": 14, "overbought": 75, "oversold": 25},
    )
    assert params_a == {"period": 14, "overbought": 70, "oversold": 30}
    assert params_b == {"period": 14, "overbought": 75, "oversold": 25}
    assert type(inst_a) is RsiStrategy
    assert type(inst_b) is RsiStrategy
    assert inst_b.overbought == 75
    assert inst_b.oversold == 25
