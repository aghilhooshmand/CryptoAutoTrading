"""Shared strategy domain (registry + all registered strategies)."""

from app.strategy import (
    bollinger as _bollinger,  # noqa: F401
    breakout as _breakout,  # noqa: F401
    dual_ema as _dual_ema,  # noqa: F401
    macd as _macd,  # noqa: F401
    rsi as _rsi,  # noqa: F401
)
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
