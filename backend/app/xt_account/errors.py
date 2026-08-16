"""XT private account errors — stable codes for Feature 013."""

from __future__ import annotations

from typing import Any

CREDENTIALS_MISSING = "credentials_missing"
AUTHENTICATION_FAILED = "authentication_failed"
TIMESTAMP_INVALID = "timestamp_invalid"
RATE_LIMITED = "rate_limited"
XT_PRIVATE_UNAVAILABLE = "xt_private_unavailable"
ORDER_NOT_FOUND = "order_not_found"

STABLE_CODES = frozenset(
    {
        CREDENTIALS_MISSING,
        AUTHENTICATION_FAILED,
        TIMESTAMP_INVALID,
        RATE_LIMITED,
        XT_PRIVATE_UNAVAILABLE,
        ORDER_NOT_FOUND,
    }
)

# XT mc → stable code (minimum map per contracts/xt-private-signing.md)
_AUTH_FAILED_MCS = frozenset(
    {
        "AUTH_001",
        "AUTH_002",
        "AUTH_003",
        "AUTH_004",
        "AUTH_005",
        "AUTH_006",
        "AUTH_007",
        "AUTH_101",
        "AUTH_102",
        "AUTH_103",
        "AUTH_104",
        "AUTH_106",
    }
)


class XtPrivateError(Exception):
    """Fail-closed private XT outcome with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in STABLE_CODES:
            raise ValueError(f"Unknown private error code: {code}")
        self.code = code
        self.message = message
        super().__init__(message)


def http_status_for_code(code: str) -> int:
    if code == CREDENTIALS_MISSING:
        return 503
    if code in (AUTHENTICATION_FAILED, TIMESTAMP_INVALID):
        return 401
    if code == RATE_LIMITED:
        return 429
    if code == ORDER_NOT_FOUND:
        return 404
    if code == XT_PRIVATE_UNAVAILABLE:
        return 502
    return 502


def map_xt_mc(mc: str | None, *, default_message: str | None = None) -> XtPrivateError:
    """Map XT envelope message code to a stable private error."""
    code = (mc or "").strip().upper()
    if code == "AUTH_105":
        return XtPrivateError(
            TIMESTAMP_INVALID,
            default_message
            or "XT rejected the request timestamp (clock skew / recv window). "
            "Check system time and NTP; the host clock was not adjusted.",
        )
    if code in _AUTH_FAILED_MCS:
        return XtPrivateError(
            AUTHENTICATION_FAILED,
            default_message or f"XT authentication failed ({code}).",
        )
    if code == "ORDER_005":
        return XtPrivateError(
            ORDER_NOT_FOUND,
            default_message or "Order was not found on the XT account.",
        )
    return XtPrivateError(
        XT_PRIVATE_UNAVAILABLE,
        default_message or f"XT private request failed ({code or 'unknown'}).",
    )


def map_http_status(status_code: int, *, body_mc: str | None = None) -> XtPrivateError | None:
    """Map transport HTTP status before/alongside envelope parsing.

    Returns None when the caller should continue parsing the body.
    HTTP 429 is handled by the rate-limit retry policy, not here.
    """
    if status_code == 401 and body_mc:
        return map_xt_mc(body_mc)
    if status_code >= 500:
        return XtPrivateError(
            XT_PRIVATE_UNAVAILABLE,
            f"XT private service returned HTTP {status_code}.",
        )
    return None


def require_success_envelope(payload: Any) -> Any:
    """Validate XT rc/mc envelope; return result or raise XtPrivateError."""
    if not isinstance(payload, dict):
        raise XtPrivateError(
            XT_PRIVATE_UNAVAILABLE,
            "Malformed XT private response envelope.",
        )
    mc = payload.get("mc")
    rc = payload.get("rc")
    if rc == 0 and (mc is None or str(mc).upper() == "SUCCESS"):
        return payload.get("result")
    raise map_xt_mc(str(mc) if mc is not None else None)
