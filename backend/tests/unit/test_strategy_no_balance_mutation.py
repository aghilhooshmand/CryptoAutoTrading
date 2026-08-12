"""SC-004 / FR-002: strategy evaluation is advisory — never mutates balances."""

from __future__ import annotations

import inspect
from decimal import Decimal
from unittest.mock import MagicMock

from app.strategy.base import CandleClose, StrategySignal
from app.strategy.dual_ema import DualEmaCrossoverStrategy
from app.strategy.registry import validate_and_materialize


def test_evaluate_signature_has_no_balance_parameters():
    sig = inspect.signature(DualEmaCrossoverStrategy.evaluate)
    params = list(sig.parameters)
    assert params == ["self", "closes"]


def test_evaluate_does_not_mutate_cash_position_or_closes():
    cash = Decimal("500")
    position_qty = Decimal("0")
    position_side = "flat"
    prices = [Decimal("100")] * 22 + [Decimal("110"), Decimal("120"), Decimal("130")]
    closes = [CandleClose(i * 60_000, p) for i, p in enumerate(prices)]
    closes_snapshot = [(c.open_time, c.close) for c in closes]

    strategy = DualEmaCrossoverStrategy()
    signal = strategy.evaluate(closes)

    assert cash == Decimal("500")
    assert position_qty == Decimal("0")
    assert position_side == "flat"
    assert [(c.open_time, c.close) for c in closes] == closes_snapshot
    assert isinstance(signal, StrategySignal)


def test_registry_strategy_evaluate_does_not_touch_mock_balances():
    """Registry-built Dual EMA still cannot see or change account state."""
    account = MagicMock()
    account.cash = Decimal("1000")
    account.position_qty = Decimal("0")

    _, _, strategy = validate_and_materialize("dual_ema", None)
    closes = [CandleClose(i * 60_000, Decimal("100")) for i in range(25)]
    strategy.evaluate(closes)

    assert account.cash == Decimal("1000")
    assert account.position_qty == Decimal("0")
    account.assert_not_called()
