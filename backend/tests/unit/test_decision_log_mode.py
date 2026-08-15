"""Unit tests for Decision Log Mode helpers."""

from app.simulation.decision_log_mode import (
    effective_decision_log_mode,
    parse_create_decision_log_mode,
    should_persist_hold,
)


def test_create_default_is_important_only():
    assert parse_create_decision_log_mode(None) == "important_only"
    assert parse_create_decision_log_mode("") == "important_only"


def test_legacy_null_effective_is_full_audit():
    assert effective_decision_log_mode(None) == "full_audit"
    assert should_persist_hold(None) is True


def test_important_only_skips_hold():
    assert should_persist_hold("important_only") is False
    assert should_persist_hold("full_audit") is True
