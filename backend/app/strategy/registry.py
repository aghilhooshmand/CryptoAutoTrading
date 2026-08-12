"""In-process strategy registry: resolve aliases, validate, materialize."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.strategy.base import Strategy
from app.strategy.params import ParamDef, StrategyParamError, validate_params


class UnknownStrategyError(Exception):
    def __init__(self, message: str = "Unknown strategy") -> None:
        super().__init__(message)
        self.code = "unknown_strategy"
        self.message = message


@dataclass
class StrategyConstraint:
    code: str
    message: str
    fields: list[str] = field(default_factory=list)


@dataclass
class StrategyRegistration:
    strategy_id: str
    display_name: str
    aliases: list[str]
    parameters: list[ParamDef]
    constraints: list[StrategyConstraint]
    factory: Callable[[dict[str, Any]], Strategy]
    validate_extra: Callable[[dict[str, Any]], None] | None = None


_REGISTRY: dict[str, StrategyRegistration] = {}
_ALIAS_TO_CANONICAL: dict[str, str] = {}


def clear_registry() -> None:
    """Test helper — wipe registrations."""
    _REGISTRY.clear()
    _ALIAS_TO_CANONICAL.clear()


def register(entry: StrategyRegistration) -> None:
    _REGISTRY[entry.strategy_id] = entry
    _ALIAS_TO_CANONICAL[entry.strategy_id] = entry.strategy_id
    for alias in entry.aliases:
        _ALIAS_TO_CANONICAL[alias] = entry.strategy_id


def resolve_canonical(strategy_id: str | None) -> str:
    if strategy_id is None or str(strategy_id).strip() == "":
        raise StrategyParamError("missing_strategy", "strategyId is required")
    key = str(strategy_id).strip()
    canonical = _ALIAS_TO_CANONICAL.get(key)
    if canonical is None:
        raise UnknownStrategyError(f"Unknown strategy: {key}")
    return canonical


def is_known_strategy_id(strategy_id: str | None) -> bool:
    if strategy_id is None or str(strategy_id).strip() == "":
        return False
    return str(strategy_id).strip() in _ALIAS_TO_CANONICAL


def get_registration(canonical_id: str) -> StrategyRegistration:
    entry = _REGISTRY.get(canonical_id)
    if entry is None:
        raise UnknownStrategyError(f"Unknown strategy: {canonical_id}")
    return entry


def list_strategies() -> list[StrategyRegistration]:
    return list(_REGISTRY.values())


def validate_and_materialize(
    strategy_id: str | None,
    strategy_params: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], Strategy]:
    """Resolve → validate → factory. Raises UnknownStrategyError / StrategyParamError."""
    canonical = resolve_canonical(strategy_id)
    entry = get_registration(canonical)
    effective = validate_params(entry.parameters, strategy_params, extra=entry.validate_extra)
    instance = entry.factory(effective)
    return canonical, effective, instance


def build_from_stored(strategy_id: str, strategy_params: dict[str, Any] | None) -> Strategy:
    """Construct for START/RESUME. Unknown stored ids raise UnknownStrategyError."""
    if not is_known_strategy_id(strategy_id):
        raise UnknownStrategyError(
            f"Cannot execute unknown strategy: {strategy_id}",
        )
    canonical, _, instance = validate_and_materialize(strategy_id, strategy_params)
    _ = canonical
    return instance


def to_api_list() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in list_strategies():
        out.append(
            {
                "id": entry.strategy_id,
                "displayName": entry.display_name,
                "aliases": list(entry.aliases),
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "label": p.label,
                        "default": p.default,
                        **({"minimum": p.minimum} if p.minimum is not None else {}),
                        **({"maximum": p.maximum} if p.maximum is not None else {}),
                        **(
                            {"exclusiveMinimum": True}
                            if p.exclusive_minimum
                            else {}
                        ),
                    }
                    for p in entry.parameters
                ],
                "constraints": [
                    {
                        "code": c.code,
                        "message": c.message,
                        "fields": list(c.fields),
                    }
                    for c in entry.constraints
                ],
            }
        )
    return out
