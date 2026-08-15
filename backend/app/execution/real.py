"""Real execution stub (Feature 012) — code/tests only; no exchange orders."""

from __future__ import annotations

from app.execution.port import ExecutionIntent, FillResult

REAL_EXECUTION_UNAVAILABLE = "real_execution_unavailable"


class RealExecutionAdapter:
    """Fails closed; never places orders or mutates trading/accounting state."""

    def execute(self, intent: ExecutionIntent) -> FillResult:
        return FillResult(
            False,
            REAL_EXECUTION_UNAVAILABLE,
            "Real execution is not available in Feature 012",
        )
