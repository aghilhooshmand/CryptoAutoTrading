"""Simulation session state machine."""

from __future__ import annotations

from enum import Enum


class SessionState(str, Enum):
    CONFIGURED = "CONFIGURED"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


_ALLOWED: dict[SessionState, set[SessionState]] = {
    SessionState.CONFIGURED: {SessionState.RUNNING},
    SessionState.RUNNING: {SessionState.STOPPING},
    SessionState.STOPPING: {SessionState.STOPPED},
    SessionState.STOPPED: set(),
}


def can_transition(current: SessionState, target: SessionState) -> bool:
    return target in _ALLOWED[current]


def transition(current: SessionState, target: SessionState) -> SessionState:
    if not can_transition(current, target):
        raise ValueError(f"Illegal transition {current.value} -> {target.value}")
    return target


def is_active(state: SessionState) -> bool:
    return state in {SessionState.RUNNING, SessionState.STOPPING}


def allows_strategy_execution(state: SessionState) -> bool:
    return state == SessionState.RUNNING
