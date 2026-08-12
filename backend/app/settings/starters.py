"""Product starter defaults for Feature 008 Settings."""

from __future__ import annotations

from typing import Any

from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str
from app.strategy.serialize import DEFAULT_DUAL_EMA_PARAMS

SINGLETON_ID = 1


def product_starter_defaults() -> dict[str, Any]:
    """Built-in starters used when no valid saved Settings exist / on Reset."""
    return {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "feeRate": as_str(DEFAULT_FEE_RATE),
        "slippageRate": as_str(DEFAULT_SLIPPAGE_RATE),
        "targetNetProfitRate": None,
        "maxSessionLossRate": None,
        "maxTrades": None,
        "strategyId": "dual_ema",
        "strategyParams": dict(DEFAULT_DUAL_EMA_PARAMS),
    }
