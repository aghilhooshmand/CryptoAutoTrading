"""Unit tests for Kraken private error mapping and rate-limit policy."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.account.credentials import KrakenCredentials
from app.account.errors import (
    AUTHENTICATION_FAILED,
    ORDER_NOT_FOUND,
    RATE_LIMITED,
    TIMESTAMP_INVALID,
    VENUE_PRIVATE_UNAVAILABLE,
    AccountPrivateError,
    map_kraken_errors,
)
from app.account.kraken_private import (
    MAX_RETRY_AFTER_WAIT_S,
    SHORT_BACKOFF_S,
    KrakenPrivateClient,
)


def test_invalid_nonce_is_timestamp_invalid() -> None:
    err = map_kraken_errors(["EAPI:Invalid nonce"])
    assert err.code == TIMESTAMP_INVALID
    assert "clock" in err.message.lower() or "nonce" in err.message.lower()


def test_invalid_key_is_authentication_failed() -> None:
    assert map_kraken_errors(["EAPI:Invalid key"]).code == AUTHENTICATION_FAILED


def test_unknown_order_is_order_not_found() -> None:
    assert map_kraken_errors(["EOrder:Unknown order"]).code == ORDER_NOT_FOUND


def test_unknown_method_is_unavailable() -> None:
    assert (
        map_kraken_errors(["EGeneral:Unknown method"]).code
        == VENUE_PRIVATE_UNAVAILABLE
    )


def test_client_has_no_clock_adjustment_api() -> None:
    forbidden = {
        "adjust_clock",
        "set_system_time",
        "sync_clock",
        "ntp_sync",
        "place_order",
        "place_market_order",
        "add_order",
        "cancel_order",
    }
    assert forbidden.isdisjoint(set(dir(KrakenPrivateClient)))


def test_rate_limit_one_retry_then_success() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.5"})
        return httpx.Response(200, json={"error": [], "result": {}})

    async def _run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api.kraken.com"
        ) as http:
            client = KrakenPrivateClient(
                KrakenCredentials("k", "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3o5TWMw="),
                client=http,
                sleep=record_sleep,
                nonce_fn=lambda: "1616492376594",
            )
            result = await client.get_balances()
            assert result == {}

    asyncio.run(_run())
    assert call_count["n"] == 2
    assert sleeps == [0.5]
    assert SHORT_BACKOFF_S == 0.5
    assert MAX_RETRY_AFTER_WAIT_S == 3.0


def test_rate_limit_retry_after_over_bound_fails_closed() -> None:
    async def _run() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "30"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api.kraken.com"
        ) as http:
            client = KrakenPrivateClient(
                KrakenCredentials("k", "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3o5TWMw="),
                client=http,
                nonce_fn=lambda: "1",
            )
            with pytest.raises(AccountPrivateError) as exc_info:
                await client.list_open_orders()
            assert exc_info.value.code == RATE_LIMITED

    asyncio.run(_run())
