"""Persist / read strategy_params JSON and normalize response ids."""

from __future__ import annotations

import json
from typing import Any

from app.strategy.registry import is_known_strategy_id, resolve_canonical
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError

DEFAULT_DUAL_EMA_PARAMS = {"fastPeriod": 9, "slowPeriod": 21}


def dumps_params(params: dict[str, Any]) -> str:
    return json.dumps(params, separators=(",", ":"), sort_keys=True)


def loads_params(raw: str | None, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if raw is None or str(raw).strip() == "":
        return dict(fallback or DEFAULT_DUAL_EMA_PARAMS)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(fallback or {})
    if not isinstance(data, dict):
        return dict(fallback or {})
    return data


def display_strategy_id(stored_id: str) -> str:
    """Normalize known aliases to canonical for API responses; keep unknown as-stored."""
    if not stored_id:
        return stored_id
    if not is_known_strategy_id(stored_id):
        return stored_id
    try:
        return resolve_canonical(stored_id)
    except (UnknownStrategyError, StrategyParamError):
        return stored_id


def effective_params_for_row(stored_id: str, raw_params: str | None) -> dict[str, Any]:
    if stored_id in ("dual_ema", "dual_ema_9_21") or (
        is_known_strategy_id(stored_id)
        and display_strategy_id(stored_id) == "dual_ema"
    ):
        return loads_params(raw_params, fallback=DEFAULT_DUAL_EMA_PARAMS)
    return loads_params(raw_params, fallback={})
