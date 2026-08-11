"""Shared strategy domain (registry + Dual EMA)."""

from app.strategy import dual_ema as _dual_ema  # noqa: F401 — register Dual EMA
from app.strategy.base import CandleClose, SignalSide, Strategy, StrategySignal
from app.strategy.registry import (
    UnknownStrategyError,
    build_from_stored,
    is_known_strategy_id,
    list_strategies,
    resolve_canonical,
    to_api_list,
    validate_and_materialize,
)

__all__ = [
    "CandleClose",
    "SignalSide",
    "Strategy",
    "StrategySignal",
    "UnknownStrategyError",
    "build_from_stored",
    "is_known_strategy_id",
    "list_strategies",
    "resolve_canonical",
    "to_api_list",
    "validate_and_materialize",
]
