"""Venue-neutral private-account errors (Feature 013 Kraken amendment)."""

from __future__ import annotations

from typing import Any, Iterable

CREDENTIALS_MISSING = "credentials_missing"
AUTHENTICATION_FAILED = "authentication_failed"
TIMESTAMP_INVALID = "timestamp_invalid"
RATE_LIMITED = "rate_limited"
VENUE_PRIVATE_UNAVAILABLE = "venue_private_unavailable"
ORDER_NOT_FOUND = "order_not_found"

STABLE_CODES = frozenset(
    {
        CREDENTIALS_MISSING,
        AUTHENTICATION_FAILED,
        TIMESTAMP_INVALID,
        RATE_LIMITED,
        VENUE_PRIVATE_UNAVAILABLE,
        ORDER_NOT_FOUND,
    }
)


class AccountPrivateError(Exception):
    """Fail-closed private-account outcome with a stable machine-readable code."""

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
    if code == VENUE_PRIVATE_UNAVAILABLE:
        return 502
    return 502


def map_kraken_errors(errors: Iterable[Any]) -> AccountPrivateError:
    """Map Kraken `error[]` strings to a stable private-account code."""
    texts = [str(item).strip() for item in errors if str(item).strip()]
    joined = " ".join(texts)
    upper = joined.upper()
    if not texts:
        return AccountPrivateError(
            VENUE_PRIVATE_UNAVAILABLE,
            "Kraken private request failed (unknown).",
        )
    if "RATE LIMIT" in upper:
        return AccountPrivateError(
            RATE_LIMITED,
            "Kraken private rate limit exceeded.",
        )
    if "INVALID NONCE" in upper:
        return AccountPrivateError(
            TIMESTAMP_INVALID,
            "Kraken rejected the request nonce (clock skew / nonce). "
            "Check system time and NTP; the host clock was not adjusted.",
        )
    if "UNKNOWN ORDER" in upper or "INVALID ORDER" in upper:
        return AccountPrivateError(
            ORDER_NOT_FOUND,
            "Order was not found on the Kraken account.",
        )
    if (
        "INVALID KEY" in upper
        or "INVALID SIGNATURE" in upper
        or "PERMISSION DENIED" in upper
    ):
        return AccountPrivateError(
            AUTHENTICATION_FAILED,
            f"Kraken authentication failed ({texts[0]}).",
        )
    return AccountPrivateError(
        VENUE_PRIVATE_UNAVAILABLE,
        f"Kraken private request failed ({texts[0]}).",
    )
