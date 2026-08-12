"""Parameter definitions and validation helpers for registered strategies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
    # When True with ``minimum`` set, value must be strictly greater than minimum.
    exclusive_minimum: bool = False


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


def _check_numeric_bounds(p: ParamDef, value: Decimal | int | float) -> None:
    if p.minimum is not None:
        lo = Decimal(str(p.minimum))
        cmp = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if p.exclusive_minimum:
            if cmp <= lo:
                raise StrategyParamError(
                    "invalid_strategy_params",
                    f"{p.name} must be > {p.minimum}",
                )
        elif cmp < lo:
            raise StrategyParamError(
                "invalid_strategy_params",
                f"{p.name} must be ≥ {p.minimum}",
            )
    if p.maximum is not None:
        hi = Decimal(str(p.maximum))
        cmp = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if cmp > hi:
            raise StrategyParamError(
                "invalid_strategy_params",
                f"{p.name} must be ≤ {p.maximum}",
            )


def _coerce_decimal_string(p: ParamDef, v: Any) -> str:
    if isinstance(v, bool):
        raise StrategyParamError(
            "invalid_strategy_params",
            f"{p.name} must be a decimal string",
        )
    if isinstance(v, Decimal):
        text = format(v, "f")
    elif isinstance(v, int):
        text = str(v)
    elif isinstance(v, float):
        text = format(Decimal(str(v)), "f")
    elif isinstance(v, str):
        text = v.strip()
        if text == "":
            raise StrategyParamError(
                "invalid_strategy_params",
                f"{p.name} must be a decimal string",
            )
    else:
        raise StrategyParamError(
            "invalid_strategy_params",
            f"{p.name} must be a decimal string",
        )
    try:
        dec = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise StrategyParamError(
            "invalid_strategy_params",
            f"{p.name} must be a decimal string",
        ) from exc
    if not dec.is_finite():
        raise StrategyParamError(
            "invalid_strategy_params",
            f"{p.name} must be a decimal string",
        )
    _check_numeric_bounds(p, dec)
    # Preserve submitted spelling for strings; normalize numbers via Decimal.
    if isinstance(v, str):
        return text
    return format(dec, "f")


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
            _check_numeric_bounds(p, iv)
            out[p.name] = iv
        elif p.type == "decimal_string":
            out[p.name] = _coerce_decimal_string(p, v)
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
