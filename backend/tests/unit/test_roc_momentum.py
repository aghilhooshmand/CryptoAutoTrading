"""ROC momentum strategy unit tests (Feature 025 US4)."""

from __future__ import annotations

from decimal import Decimal

from app.strategy.base import CandleClose, SignalSide
from app.strategy.momentum_roc import RocMomentumStrategy
from app.strategy.registry import validate_and_materialize


def _closes(prices: list[str]) -> list[CandleClose]:
    return [
        CandleClose(open_time=i * 60_000, close=Decimal(p), open=Decimal(p), high=Decimal(p), low=Decimal(p))
        for i, p in enumerate(prices)
    ]


def test_warmup():
    s = RocMomentumStrategy(period=3, buy_threshold="0", sell_threshold="0")
    assert s.min_history_candles() == 4
    assert s.evaluate(_closes(["100", "101", "102"])).reason_code == "warmup"


def test_buy_on_roc_cross_above_zero():
    # period=3: ROC becomes positive after flat/negative then rise
    # prices: enough history then dip then recover
    prices = ["100", "100", "100", "99", "98", "97", "100", "105"]
    s = RocMomentumStrategy(period=3, buy_threshold="0", sell_threshold="0")
    sides = [s.evaluate(_closes(prices[:n])).side for n in range(1, len(prices) + 1)]
    assert SignalSide.BUY in sides


def test_sell_on_roc_cross_below_zero():
    prices = ["100", "102", "104", "106", "108", "110", "100", "95"]
    s = RocMomentumStrategy(period=3, buy_threshold="0", sell_threshold="0")
    sides = [s.evaluate(_closes(prices[:n])).side for n in range(1, len(prices) + 1)]
    assert SignalSide.SELL in sides


def test_factory_registers():
    _id, params, strat = validate_and_materialize(
        "roc_momentum",
        {"period": 12, "buyThreshold": "0", "sellThreshold": "0"},
    )
    assert _id == "roc_momentum"
    assert params["period"] == 12
    assert strat.min_history_candles() == 13
