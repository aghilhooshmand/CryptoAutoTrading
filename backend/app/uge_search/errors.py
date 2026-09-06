"""UGE search domain errors (Feature 019 / 020)."""

from __future__ import annotations

INVALID_SPLIT = "invalid_split"
UNKNOWN_FITNESS_ID = "unknown_fitness_id"
UGE_RUN_FAILED = "uge_run_failed"
PERSIST_FAILED = "persist_failed"
INVALID_EXPERIMENT_CONFIG = "invalid_experiment_config"
EXPERIMENT_NOT_FOUND = "experiment_not_found"
EXPERIMENT_NOT_TERMINAL = "experiment_not_terminal"
DUPLICATE_DISPLAY_NAME = "duplicate_display_name"
FREEZE_FAILED = "freeze_failed"
INVALID_SEARCH_SPACE = "invalid_search_space"

ERROR_CODES = frozenset(
    {
        INVALID_SPLIT,
        UNKNOWN_FITNESS_ID,
        UGE_RUN_FAILED,
        PERSIST_FAILED,
        INVALID_EXPERIMENT_CONFIG,
        EXPERIMENT_NOT_FOUND,
        EXPERIMENT_NOT_TERMINAL,
        DUPLICATE_DISPLAY_NAME,
        FREEZE_FAILED,
        INVALID_SEARCH_SPACE,
    }
)


class UgeSearchError(Exception):
    def __init__(self, code: str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Unknown uge search error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message

    def to_error_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}
