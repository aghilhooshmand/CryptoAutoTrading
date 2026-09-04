"""Stable Torque bind / evaluate error codes (Feature 016)."""

from __future__ import annotations

INVALID_TORQUE_FORM = "invalid_torque_form"
UNKNOWN_TORQUE_LEAF = "unknown_torque_leaf"
INVALID_TORQUE_PARAMS = "invalid_torque_params"
INVALID_COMPOSITION = "invalid_composition"
EVALUATE_FAILED = "evaluate_failed"

ERROR_CODES = frozenset(
    {
        INVALID_TORQUE_FORM,
        UNKNOWN_TORQUE_LEAF,
        INVALID_TORQUE_PARAMS,
        INVALID_COMPOSITION,
        EVALUATE_FAILED,
    }
)


class TorqueBindError(Exception):
    """Domain error for phenotype check / bind / evaluate failures."""

    def __init__(self, code: str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Unknown torque bind error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message

    def to_error_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}
