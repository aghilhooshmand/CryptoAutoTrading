"""Parameter definitions and validation helpers for registered strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class StrategyParamError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ParamDef:
    name: str
    type: str  # "integer" | "decimal_string" | "string"
    label: str
    default: Any
    required: bool = False
    minimum: int | float | None = None
    maximum: int | float | None = None


def merge_defaults(defs: list[ParamDef], submitted: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(submitted or {})
    out: dict[str, Any] = {}
    for p in defs:
        if p.name in raw and raw[p.name] is not None:
            out[p.name] = raw[p.name]
        elif p.default is not None:
            out[p.name] = p.default
        elif p.required:
            raise StrategyParamError(
                "invalid_strategy_params",
                f"Missing required strategy parameter: {p.name}",
            )
    return out


def coerce_and_bounds(defs: list[ParamDef], values: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in defs:
        if p.name not in values:
            continue
        v = values[p.name]
        if p.type == "integer":
            try:
                if isinstance(v, bool):
                    raise ValueError
                iv = int(v)
            except (TypeError, ValueError) as exc:
                raise StrategyParamError(
                    "invalid_strategy_params",
                    f"{p.name} must be an integer",
                ) from exc
            if p.minimum is not None and iv < p.minimum:
                raise StrategyParamError(
                    "invalid_strategy_params",
                    f"{p.name} must be ≥ {p.minimum}",
                )
            if p.maximum is not None and iv > p.maximum:
                raise StrategyParamError(
                    "invalid_strategy_params",
                    f"{p.name} must be ≤ {p.maximum}",
                )
            out[p.name] = iv
        else:
            out[p.name] = v
    return out


def validate_params(
    defs: list[ParamDef],
    submitted: dict[str, Any] | None,
    *,
    extra: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    merged = merge_defaults(defs, submitted)
    coerced = coerce_and_bounds(defs, merged)
    if extra is not None:
        extra(coerced)
    return coerced
