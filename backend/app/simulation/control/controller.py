"""Trading controller — session activity and stop authority."""

from __future__ import annotations

from dataclasses import dataclass

from app.simulation.state_machine import SessionState, allows_strategy_execution
from app.simulation.strategy.base import SignalSide, StrategySignal


@dataclass
class ControlDecision:
    approved: bool
    reason_code: str | None = None
    reason_message: str | None = None


class TradingController:
    def review(self, state: SessionState, signal: StrategySignal, emergency: bool = False) -> ControlDecision:
        if emergency:
            return ControlDecision(False, "emergency_stop_active", "Emergency stop active")
        if not allows_strategy_execution(state):
            return ControlDecision(False, "session_not_active", f"Session state is {state.value}")
        if signal.side == SignalSide.HOLD:
            return ControlDecision(True)
        return ControlDecision(True)
