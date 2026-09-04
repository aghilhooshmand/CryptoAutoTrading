"""Leaf and composition name catalogue + ParamDef metadata (Feature 016)."""

from __future__ import annotations

from typing import Any

from app.strategy.registry import get_registration, is_known_strategy_id, resolve_canonical

# MVP leaves (SC-001 minimum). Other registry strategies MAY be allowed at bind time.
MVP_LEAF_IDS: frozenset[str] = frozenset({"rsi", "macd", "dual_ema"})

# Instruction name (lowercase) → canonical op
_COMPOSITION_ALIASES: dict[str, str] = {
    "and": "and",
    "or": "or",
    "vote": "vote",
}

COMPOSITION_OPS: frozenset[str] = frozenset(_COMPOSITION_ALIASES.values())


def normalize_composition_op(name: str) -> str | None:
    """Return canonical op or None if not a composition instruction."""
    key = str(name).strip()
    # Case aliases: And → and (research R5)
    return _COMPOSITION_ALIASES.get(key.lower())


def is_composition_name(name: str) -> bool:
    return normalize_composition_op(name) is not None


def resolve_leaf_id(name: str) -> str | None:
    """
    Resolve instruction name to a registry strategy id (case-insensitive).

    MVP catalogue advertises rsi/macd/dual_ema; any known registry id is allowed
    if ParamDefs map cleanly (research R6).
    """
    raw = str(name).strip()
    if not raw:
        return None
    if is_known_strategy_id(raw):
        return resolve_canonical(raw)
    lower = raw.lower()
    if is_known_strategy_id(lower):
        return resolve_canonical(lower)
    # Scan registry for case-insensitive match
    from app.strategy.registry import list_strategies

    for entry in list_strategies():
        if entry.strategy_id.lower() == lower:
            return entry.strategy_id
        for alias in entry.aliases:
            if alias.lower() == lower:
                return entry.strategy_id
    return None


def leaf_param_metadata(strategy_id: str) -> list[dict[str, Any]]:
    """Expose ParamDef names/types/bounds for bind + later Feature 019 BNF."""
    entry = get_registration(strategy_id)
    out: list[dict[str, Any]] = []
    for p in entry.parameters:
        item: dict[str, Any] = {
            "name": p.name,
            "type": p.type,
            "label": p.label,
            "default": p.default,
        }
        if p.minimum is not None:
            item["minimum"] = p.minimum
        if p.maximum is not None:
            item["maximum"] = p.maximum
        if p.exclusive_minimum:
            item["exclusiveMinimum"] = True
        out.append(item)
    return out


def mvp_leaf_catalogue() -> list[dict[str, Any]]:
    """Allow-list metadata for MVP leaves (FR-002)."""
    rows: list[dict[str, Any]] = []
    for sid in sorted(MVP_LEAF_IDS):
        rows.append(
            {
                "strategyId": sid,
                "parameters": leaf_param_metadata(sid),
            }
        )
    return rows
