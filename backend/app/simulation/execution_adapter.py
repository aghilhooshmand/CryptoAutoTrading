"""Select execution engine by session mode (Feature 015)."""

from __future__ import annotations

from app.db.models import SimulationSessionRow
from app.execution.port import ExecutionEngine
from app.execution.real import RealExecutionAdapter
from app.execution.simulation import SimulationExecutionEngine


def execution_engine_for(row: SimulationSessionRow) -> ExecutionEngine:
    if row.mode == "real":
        return RealExecutionAdapter(enabled=True)
    return SimulationExecutionEngine()
