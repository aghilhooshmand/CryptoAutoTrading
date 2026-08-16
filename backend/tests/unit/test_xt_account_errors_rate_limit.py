"""Unit tests for XT private error mapping and rate-limit policy."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.xt_account.client import (
    MAX_RETRY_AFTER_WAIT_S,
    SHORT_BACKOFF_S,
    XtPrivateClient,
)
from app.xt_account.credentials import PrivateCredentials
from app.xt_account.errors import (
    AUTHENTICATION_FAILED,
    ORDER_NOT_FOUND,
    RATE_LIMITED,
    TIMESTAMP_INVALID,
    XT_PRIVATE_UNAVAILABLE,
    XtPrivateError,
    map_xt_mc,
    require_success_envelope,
)


def test_auth_105_is_timestamp_invalid() -> None:
    err = map_xt_mc("AUTH_105")
    assert err.code == TIMESTAMP_INVALID
    assert "clock" in err.message.lower() or "timestamp" in err.message.lower()


def test_auth_103_is_authentication_failed() -> None:
    assert map_xt_mc("AUTH_103").code == AUTHENTICATION_FAILED


def test_order_005_is_order_not_found() -> None:
    assert map_xt_mc("ORDER_005").code == ORDER_NOT_FOUND


def test_require_success_envelope_raises_timestamp() -> None:
    with pytest.raises(XtPrivateError) as exc_info:
        require_success_envelope({"rc": 1, "mc": "AUTH_105", "result": None})
    assert exc_info.value.code == TIMESTAMP_INVALID


def test_client_has_no_clock_adjustment_api() -> None:
    """FR-010a / FR-017: never auto-adjust the host system clock."""
    forbidden = {
        "adjust_clock",
        "set_system_time",
        "sync_clock",
        "ntp_sync",
    }
    assert forbidden.isdisjoint(set(dir(XtPrivateClient)))


def test_rate_limit_one_retry_then_success() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.5"})
        return httpx.Response(
            200,
            json={"rc": 0, "mc": "SUCCESS", "result": {"assets": []}},
        )

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://sapi.xt.com"
        ) as http:
            client = XtPrivateClient(
                PrivateCredentials("key", "secret"),
                client=http,
                sleep=record_sleep,
                clock_ms=lambda: "1641446237201",
            )
            result = await client.get_balances()
        assert result == {"assets": []}
        assert call_count["n"] == 2
        assert sleeps == [0.5]

    asyncio.run(_run())


def test_rate_limit_retry_after_over_bound_no_retry() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, headers={"Retry-After": str(MAX_RETRY_AFTER_WAIT_S + 1)}
        )

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://sapi.xt.com"
        ) as http:
            client = XtPrivateClient(
                PrivateCredentials("key", "secret"),
                client=http,
                sleep=record_sleep,
                clock_ms=lambda: "1641446237201",
            )
            with pytest.raises(XtPrivateError) as exc_info:
                await client.get_balances()
        assert exc_info.value.code == RATE_LIMITED
        assert sleeps == []

    asyncio.run(_run())


def test_rate_limit_second_429_after_short_backoff() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://sapi.xt.com"
        ) as http:
            client = XtPrivateClient(
                PrivateCredentials("key", "secret"),
                client=http,
                sleep=record_sleep,
                clock_ms=lambda: "1641446237201",
            )
            with pytest.raises(XtPrivateError) as exc_info:
                await client.get_balances()
        assert exc_info.value.code == RATE_LIMITED
        assert sleeps == [SHORT_BACKOFF_S]

    asyncio.run(_run())


def test_timestamp_invalid_from_exchange() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"rc": 1, "mc": "AUTH_105", "result": None},
        )

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://sapi.xt.com"
        ) as http:
            client = XtPrivateClient(
                PrivateCredentials("key", "secret"),
                client=http,
                clock_ms=lambda: "1641446237201",
            )
            with pytest.raises(XtPrivateError) as exc_info:
                await client.get_balances()
        assert exc_info.value.code == TIMESTAMP_INVALID

    asyncio.run(_run())


def test_server_error_maps_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://sapi.xt.com"
        ) as http:
            client = XtPrivateClient(
                PrivateCredentials("key", "secret"),
                client=http,
                clock_ms=lambda: "1",
            )
            with pytest.raises(XtPrivateError) as exc_info:
                await client.get_balances()
        assert exc_info.value.code == XT_PRIVATE_UNAVAILABLE

    asyncio.run(_run())
