"""HistoricalExecutionAdapter — re-export from app.execution (Feature 012)."""

from app.execution.historical import HistoricalExecutionAdapter, HistoricalFillResult

__all__ = ["HistoricalExecutionAdapter", "HistoricalFillResult"]
