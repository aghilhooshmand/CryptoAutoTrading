"""Bounded public market-data retry (Feature 014 FR-012 / research R5)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.market_data.adapters.base import MarketDataAdapterError

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_BACKOFF_S = 0.5
MAX_RETRY_AFTER_S = 2.0
MAX_RETRIES = 1  # one re-attempt after first failure


class PublicRetryExhausted(Exception):
    """Raised when the public read failed after bounded retries (or was not retryable)."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause


def parse_retry_after(header_value: str | None) -> float | None:
    if header_value is None or header_value == "":
        return None
    text = header_value.strip()
    try:
        return float(text)
    except ValueError:
        return None


def _retry_after_from_exc(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    return parse_retry_after(headers.get("Retry-After"))


def is_retryable_public_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, asyncio.TimeoutError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return True
        return code >= 500
    if isinstance(exc, MarketDataAdapterError):
        # Adapter wraps transport / 5xx as MarketDataAdapterError — retryable.
        # Unsupported / permanent contract errors use code "unsupported".
        return getattr(exc, "code", "") != "unsupported"
    # Nested cause (e.g. adapter wraps httpx)
    cause = getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return is_retryable_public_error(cause)
    return False


async def with_public_retry(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    default_backoff_s: float = DEFAULT_BACKOFF_S,
    max_retry_after_s: float = MAX_RETRY_AFTER_S,
) -> T:
    """Execute a public market-data call with at most one retry.

    - Default backoff 0.5s when no usable Retry-After.
    - If Retry-After > max_retry_after_s (2.0), do not retry — raise immediately.
    - Eligible: timeout, connection error, HTTP 5xx, 429 (when wait ≤ cap),
      transient MarketDataAdapterError (not unsupported).
    """
    sleep_fn = sleep or asyncio.sleep
    try:
        return await coro_factory()
    except Exception as first:  # noqa: BLE001
        if not is_retryable_public_error(first):
            raise
        wait = _retry_after_from_exc(first)
        if wait is None:
            wait = default_backoff_s
        if wait > max_retry_after_s:
            logger.info(
                "public_retry skip wait=%.3f exceeds cap=%.3f",
                wait,
                max_retry_after_s,
            )
            raise PublicRetryExhausted(
                f"Retry-After {wait}s exceeds cap {max_retry_after_s}s",
                cause=first,
            ) from first
        logger.info("public_retry attempt=2 wait=%.3f error=%s", wait, type(first).__name__)
        await sleep_fn(wait)
        try:
            return await coro_factory()
        except Exception as second:  # noqa: BLE001
            raise PublicRetryExhausted(
                "Public market-data call failed after one retry",
                cause=second,
            ) from second
