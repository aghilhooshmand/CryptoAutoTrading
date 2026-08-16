"""Public market-data retry bounds (Feature 014 FR-012)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.market_data.adapters.base import MarketDataAdapterError
from app.market_data.public_retry import (
    DEFAULT_BACKOFF_S,
    MAX_RETRY_AFTER_S,
    PublicRetryExhausted,
    is_retryable_public_error,
    parse_retry_after,
    with_public_retry,
)


def test_parse_retry_after():
    assert parse_retry_after("1.5") == 1.5
    assert parse_retry_after(None) is None
    assert parse_retry_after("nope") is None


def test_retryable_errors():
    assert is_retryable_public_error(httpx.TimeoutException("t"))
    assert is_retryable_public_error(MarketDataAdapterError("down"))
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(503, request=req)
    assert is_retryable_public_error(httpx.HTTPStatusError("e", request=req, response=resp))
    resp4 = httpx.Response(400, request=req)
    assert not is_retryable_public_error(httpx.HTTPStatusError("e", request=req, response=resp4))


def test_max_one_retry_default_backoff():
    sleeps: list[float] = []
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return "ok"

    async def sleep(s: float):
        sleeps.append(s)

    result = asyncio.run(with_public_retry(factory, sleep=sleep))
    assert result == "ok"
    assert calls["n"] == 2
    assert sleeps == [DEFAULT_BACKOFF_S]


def test_retry_after_capped():
    sleeps: list[float] = []
    calls = {"n": 0}
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(429, headers={"Retry-After": "1.0"}, request=req)

    async def factory():
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.HTTPStatusError("rl", request=req, response=resp)
        return "ok"

    async def sleep(s: float):
        sleeps.append(s)

    result = asyncio.run(with_public_retry(factory, sleep=sleep))
    assert result == "ok"
    assert sleeps == [1.0]


def test_retry_after_exceeds_cap_no_retry():
    calls = {"n": 0}
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(429, headers={"Retry-After": "5.0"}, request=req)

    async def factory():
        calls["n"] += 1
        raise httpx.HTTPStatusError("rl", request=req, response=resp)

    async def sleep(_s: float):
        pytest.fail("should not sleep")

    with pytest.raises(PublicRetryExhausted):
        asyncio.run(with_public_retry(factory, sleep=sleep))
    assert calls["n"] == 1
    assert MAX_RETRY_AFTER_S == 2.0


def test_exhausted_after_second_failure():
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        raise httpx.TimeoutException("t")

    async def sleep(_s: float):
        return None

    with pytest.raises(PublicRetryExhausted):
        asyncio.run(with_public_retry(factory, sleep=sleep))
    assert calls["n"] == 2
