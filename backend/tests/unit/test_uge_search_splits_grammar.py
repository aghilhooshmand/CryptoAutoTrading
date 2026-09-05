"""Splits, fitness ids, grammar load (Feature 019 foundation)."""

from __future__ import annotations

import pytest

from app.uge_search.errors import UgeSearchError
from app.uge_search.fitness import (
    DEFAULT_FITNESS_ID,
    FITNESS_ALLOW_LIST,
    resolve_fitness_id,
    scalar_from_metrics,
)
from app.uge_search.grammar_mvp import GRAMMAR_ID, load_trading_mvp_grammar, trading_mvp_bnf_text
from app.uge_search.splits import chronological_split


def test_chronological_split_ratios_and_order():
    items = list(range(10))
    split = chronological_split(items)
    assert split.train == [0, 1, 2, 3, 4, 5]
    assert split.validation == [6, 7]
    assert split.test == [8, 9]
    assert split.train + split.validation + split.test == items


def test_chronological_split_rejects_bad_ratios():
    with pytest.raises(UgeSearchError) as ei:
        chronological_split([1, 2, 3, 4], train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)
    assert ei.value.code == "invalid_split"


def test_fitness_allow_list():
    assert resolve_fitness_id(None) == DEFAULT_FITNESS_ID
    assert resolve_fitness_id("net_profit") == "net_profit"
    assert "net_minus_bh" in FITNESS_ALLOW_LIST
    with pytest.raises(UgeSearchError):
        resolve_fitness_id("sharpe")


def test_scalar_from_metrics():
    metrics = {"netProfit": "10", "buyAndHoldNetProfit": "3"}
    assert scalar_from_metrics("net_minus_bh", metrics) == 7.0
    assert scalar_from_metrics("net_profit", metrics) == 10.0


def test_load_trading_mvp_grammar():
    text = trading_mvp_bnf_text()
    assert "rsi" in text and "dual_ema" in text and "macd" in text
    assert "and(" in text and "vote(" in text
    g = load_trading_mvp_grammar()
    assert g is not None
    assert GRAMMAR_ID == "trading_mvp"
