"""UGE search domain errors (Feature 019)."""

from __future__ import annotations

INVALID_SPLIT = "invalid_split"
UNKNOWN_FITNESS_ID = "unknown_fitness_id"
UGE_RUN_FAILED = "uge_run_failed"
PERSIST_FAILED = "persist_failed"

ERROR_CODES = frozenset(
    {
        INVALID_SPLIT,
        UNKNOWN_FITNESS_ID,
        UGE_RUN_FAILED,
        PERSIST_FAILED,
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
