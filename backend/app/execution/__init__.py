"""Mode-neutral execution package (Feature 012).

Call-site inventory: specs/012-execution-abstraction/call-sites.md
"""

from app.execution.historical import HistoricalExecutionAdapter, HistoricalFillResult
from app.execution.port import ExecutionEngine, ExecutionIntent, FillResult
from app.execution.real import REAL_EXECUTION_UNAVAILABLE, RealExecutionAdapter
from app.execution.simulation import SimulationExecutionEngine

__all__ = [
    "ExecutionEngine",
    "ExecutionIntent",
    "FillResult",
    "HistoricalExecutionAdapter",
    "HistoricalFillResult",
    "REAL_EXECUTION_UNAVAILABLE",
    "RealExecutionAdapter",
    "SimulationExecutionEngine",
]
