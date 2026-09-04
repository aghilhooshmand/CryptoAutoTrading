"""check_phenotype / bind_phenotype success and fail-closed (Feature 016 US1)."""

from __future__ import annotations

import pytest

from app.strategy.base import SignalSide
from app.torque_bind import (
    CompositeStrategy,
    INVALID_TORQUE_FORM,
    INVALID_TORQUE_PARAMS,
    UNKNOWN_TORQUE_LEAF,
    TorqueBindError,
    bind_phenotype,
    check_phenotype,
    combine_and,
    combine_or,
    combine_vote,
)
from app.torque_bind.bind import bind_to_program


def test_check_valid_leaf():
    r = check_phenotype("rsi(period=14)")
    assert r.ok
    assert r.program is not None
    assert r.error is None


def test_check_invalid_form():
    r = check_phenotype("not a program!!!")
    assert not r.ok
    assert r.error is not None
    assert r.error.code == INVALID_TORQUE_FORM


def test_bind_leaf_rsi():
    strategy = bind_phenotype("rsi(period=14, oversold=30, overbought=70)")
    assert strategy.min_history_candles() >= 1
    assert not isinstance(strategy, CompositeStrategy)


def test_bind_and_composite():
    strategy = bind_phenotype(
        "and(rsi(period=14), macd(fastPeriod=12, slowPeriod=26, signalPeriod=9))"
    )
    assert isinstance(strategy, CompositeStrategy)
    assert strategy.op == "and"
    assert len(strategy.children) == 2


def test_unknown_leaf_fail_closed():
    with pytest.raises(TorqueBindError) as ei:
        bind_phenotype("foo(period=1)")
    assert ei.value.code == UNKNOWN_TORQUE_LEAF


def test_invalid_params_fail_closed():
    with pytest.raises(TorqueBindError) as ei:
        bind_phenotype("rsi(period=1)")  # period minimum is 2
    assert ei.value.code == INVALID_TORQUE_PARAMS


def test_positional_leaf_args_rejected():
    with pytest.raises(TorqueBindError) as ei:
        bind_phenotype("rsi(14)")
    assert ei.value.code == INVALID_TORQUE_PARAMS


def test_composition_requires_two_children():
    with pytest.raises(TorqueBindError) as ei:
        bind_phenotype("and(rsi(period=14))")
    assert ei.value.code == "invalid_composition"


def test_effective_leaves_collected():
    program = bind_to_program(
        "vote(dual_ema(fastPeriod=9, slowPeriod=21), rsi(period=14))"
    )
    from app.torque_bind.bind import collect_effective_leaves

    leaves = collect_effective_leaves(program.root)
    assert [x["strategyId"] for x in leaves] == ["dual_ema", "rsi"]


def test_combinators_r5():
    assert combine_and([SignalSide.BUY, SignalSide.BUY]) == SignalSide.BUY
    assert combine_and([SignalSide.BUY, SignalSide.SELL]) == SignalSide.HOLD
    assert combine_or([SignalSide.BUY, SignalSide.HOLD]) == SignalSide.BUY
    assert combine_or([SignalSide.BUY, SignalSide.SELL]) == SignalSide.HOLD
    assert combine_vote([SignalSide.BUY, SignalSide.BUY, SignalSide.SELL]) == SignalSide.BUY
    assert combine_vote([SignalSide.BUY, SignalSide.SELL]) == SignalSide.HOLD
