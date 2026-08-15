"""Simulation execution adapter (Feature 012)."""

from __future__ import annotations

from app.execution.economics import execute_fill
from app.execution.port import ExecutionIntent, FillResult


class SimulationExecutionEngine:
    """Thin Simulation adapter — journals and Portfolio apply stay in callers."""

    def execute(self, intent: ExecutionIntent) -> FillResult:
        return execute_fill(intent)
