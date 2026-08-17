"""Kraken private REST client — read-only (Feature 013 amendment)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Mapping, Optional

import httpx

from app.account.credentials import KrakenCredentials
from app.account.errors import (
    RATE_LIMITED,
    VENUE_PRIVATE_UNAVAILABLE,
    AccountPrivateError,
    map_kraken_errors,
)
from app.account.signing import encode_postdata, signed_headers

KRAKEN_PRIVATE_BASE = "https://api.kraken.com"
DEFAULT_TIMEOUT = 10.0
MAX_RETRY_AFTER_WAIT_S = 3.0
SHORT_BACKOFF_S = 0.5

SleepFn = Callable[[float], Awaitable[None]]


async def _default_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _parse_retry_after(header_value: str | None) -> Optional[float]:
    if header_value is None or header_value == "":
        return None
    text = header_value.strip()
    try:
        return float(text)
    except ValueError:
        return None


class KrakenPrivateClient:
    """Signed Kraken private client — balances, open orders, order lookup only."""

    def __init__(
        self,
        credentials: KrakenCredentials,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = KRAKEN_PRIVATE_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        sleep: SleepFn = _default_sleep,
        nonce_fn: Callable[[], str] | None = None,
    ) -> None:
        self._credentials = credentials
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._sleep = sleep
        self._nonce_fn = nonce_fn or (lambda: str(int(time.time() * 1000)))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_balances(self) -> Any:
        try:
            return await self._private_post("/0/private/BalanceEx")
        except AccountPrivateError as exc:
            if exc.code != VENUE_PRIVATE_UNAVAILABLE or "Unknown method" not in exc.message:
                raise
            return await self._private_post("/0/private/Balance")

    async def list_open_orders(self, venue_product_id: str | None = None) -> Any:
        del venue_product_id  # filtered after normalize; Kraken OpenOrders is unfiltered
        return await self._private_post("/0/private/OpenOrders")

    async def get_order(self, venue_order_id: str) -> Any:
        return await self._private_post(
            "/0/private/QueryOrders",
            extra={"txid": venue_order_id},
        )

    async def _private_post(
        self,
        url_path: str,
        *,
        extra: Mapping[str, str] | None = None,
        _retried: bool = False,
    ) -> Any:
        nonce = self._nonce_fn()
        data: dict[str, str] = {"nonce": nonce}
        if extra:
            data.update(extra)
        postdata = encode_postdata(data)
        headers = signed_headers(
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
            url_path=url_path,
            postdata=postdata,
            nonce=nonce,
        )
        try:
            response = await self._client.post(
                url_path,
                headers=headers,
                content=postdata.encode(),
            )
        except httpx.TimeoutException as exc:
            raise AccountPrivateError(
                VENUE_PRIVATE_UNAVAILABLE,
                "Kraken private request timed out.",
            ) from exc
        except httpx.HTTPError as exc:
            raise AccountPrivateError(
                VENUE_PRIVATE_UNAVAILABLE,
                "Kraken private request failed due to a network error.",
            ) from exc

        if response.status_code == 429:
            return await self._handle_rate_limit(
                url_path,
                extra=extra,
                response=response,
                retried=_retried,
            )

        payload = self._parse_json(response)
        errors = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(errors, list) and errors:
            mapped = map_kraken_errors(errors)
            if mapped.code == RATE_LIMITED:
                return await self._handle_rate_limit(
                    url_path,
                    extra=extra,
                    response=response,
                    retried=_retried,
                )
            raise mapped
        if response.status_code != 200:
            raise AccountPrivateError(
                VENUE_PRIVATE_UNAVAILABLE,
                f"Kraken private service returned HTTP {response.status_code}.",
            )
        if not isinstance(payload, dict):
            raise AccountPrivateError(
                VENUE_PRIVATE_UNAVAILABLE,
                "Malformed Kraken private response envelope.",
            )
        return payload.get("result")

    def _parse_json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise AccountPrivateError(
                VENUE_PRIVATE_UNAVAILABLE,
                f"Kraken private service returned HTTP {response.status_code} "
                "with a non-JSON body."
                if response.status_code >= 400
                else "Malformed Kraken private JSON response.",
            ) from exc

    async def _handle_rate_limit(
        self,
        url_path: str,
        *,
        extra: Mapping[str, str] | None,
        response: httpx.Response,
        retried: bool,
    ) -> Any:
        if retried:
            raise AccountPrivateError(
                RATE_LIMITED,
                "Kraken private rate limit exceeded after one retry.",
            )
        delay = _parse_retry_after(response.headers.get("Retry-After"))
        if delay is None:
            delay = SHORT_BACKOFF_S
        if delay > MAX_RETRY_AFTER_WAIT_S:
            raise AccountPrivateError(
                RATE_LIMITED,
                "Kraken private rate limited; Retry-After exceeds the allowed wait bound.",
            )
        await self._sleep(delay)
        return await self._private_post(url_path, extra=extra, _retried=True)
