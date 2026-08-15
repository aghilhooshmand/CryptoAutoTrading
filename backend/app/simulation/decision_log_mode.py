"""Effective Simulation decision_log_mode helpers (Decision Log Mode amendment)."""

from __future__ import annotations

DECISION_LOG_IMPORTANT_ONLY = "important_only"
DECISION_LOG_FULL_AUDIT = "full_audit"
DECISION_LOG_MODES = frozenset({DECISION_LOG_IMPORTANT_ONLY, DECISION_LOG_FULL_AUDIT})


def normalize_decision_log_mode(raw: str | None) -> str:
    """API/effective mode: legacy NULL/missing → full_audit."""
    if raw is None or raw == "":
        return DECISION_LOG_FULL_AUDIT
    value = str(raw).strip()
    if value not in DECISION_LOG_MODES:
        raise ValueError(f"decisionLogMode must be one of: {sorted(DECISION_LOG_MODES)}")
    return value


def parse_create_decision_log_mode(raw: object | None) -> str:
    """New-session create default is important_only when omitted."""
    if raw is None or raw == "":
        return DECISION_LOG_IMPORTANT_ONLY
    return normalize_decision_log_mode(str(raw))


def effective_decision_log_mode(row_mode: str | None) -> str:
    return normalize_decision_log_mode(row_mode)


def should_persist_hold(row_mode: str | None) -> bool:
    return effective_decision_log_mode(row_mode) == DECISION_LOG_FULL_AUDIT
