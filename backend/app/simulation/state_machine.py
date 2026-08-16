"""Simulation session state machine."""

from __future__ import annotations

from enum import Enum


class SessionState(str, Enum):
    CONFIGURED = "CONFIGURED"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"
    STOPPED = "STOPPED"


# Legal transitions (Feature 014):
#   CONFIGURED → RUNNING
#   RUNNING → STOPPING | RECOVERY_BLOCKED
#   STOPPING → STOPPED | RECOVERY_BLOCKED
#   RECOVERY_BLOCKED → RUNNING | STOPPING
#   STOPPED → ∅ (terminal)
_ALLOWED: dict[SessionState, set[SessionState]] = {
    SessionState.CONFIGURED: {SessionState.RUNNING},
    SessionState.RUNNING: {SessionState.STOPPING, SessionState.RECOVERY_BLOCKED},
    SessionState.STOPPING: {
        SessionState.STOPPED,
        SessionState.RECOVERY_BLOCKED,
        SessionState.RUNNING,
    },
    SessionState.RECOVERY_BLOCKED: {SessionState.RUNNING, SessionState.STOPPING},
    SessionState.STOPPED: set(),
}


def can_transition(current: SessionState, target: SessionState) -> bool:
    return target in _ALLOWED[current]


def transition(current: SessionState, target: SessionState) -> SessionState:
    if not can_transition(current, target):
        raise ValueError(f"Illegal transition {current.value} -> {target.value}")
    return target


def recover_to_blocked(current: SessionState) -> SessionState:
    """RUNNING|STOPPING → RECOVERY_BLOCKED (startup / resume gate failure)."""
    return transition(current, SessionState.RECOVERY_BLOCKED)


def is_active(state: SessionState) -> bool:
    return state in {
        SessionState.RUNNING,
        SessionState.STOPPING,
        SessionState.RECOVERY_BLOCKED,
    }


def allows_strategy_execution(state: SessionState) -> bool:
    return state == SessionState.RUNNING
