"""XT Spot private REST client — read-only (Feature 013)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Mapping, Optional

import httpx

from app.xt_account.credentials import PrivateCredentials
from app.xt_account.errors import (
    RATE_LIMITED,
    XT_PRIVATE_UNAVAILABLE,
    XtPrivateError,
    require_success_envelope,
)
from app.xt_account.signing import signed_headers, sorted_query_string

XT_SPOT_BASE = "https://sapi.xt.com"
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


class XtPrivateClient:
    """Signed XT Spot private client — reads (013) + market place (015, adapter-only)."""

    def __init__(
        self,
        credentials: PrivateCredentials,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = XT_SPOT_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        sleep: SleepFn = _default_sleep,
        clock_ms: Callable[[], str] | None = None,
    ) -> None:
        self._credentials = credentials
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._sleep = sleep
        self._clock_ms = clock_ms or (lambda: str(int(time.time() * 1000)))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_balances(self) -> Any:
        return await self._signed_get("/v4/balances")

    async def list_open_orders(self, symbol: str | None = None) -> Any:
        params: dict[str, str] = {}
        if symbol:
            params["symbol"] = symbol
        return await self._signed_get("/v4/open-order", params=params or None)

    async def get_order(self, order_id: str) -> Any:
        return await self._signed_get(f"/v4/order/{order_id}")

    async def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | None = None,
        quote_qty: str | None = None,
    ) -> Any:
        """Place SPOT MARKET order. Only RealExecutionAdapter should call this."""
        side_u = side.upper()
        if side_u not in ("BUY", "SELL"):
            raise XtPrivateError(XT_PRIVATE_UNAVAILABLE, "Invalid order side.")
        if (quantity is None) == (quote_qty is None):
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                "Market order requires exactly one of quantity or quoteQty.",
            )
        body: dict[str, str] = {
            "symbol": symbol,
            "side": side_u,
            "type": "MARKET",
            "bizType": "SPOT",
        }
        if quantity is not None:
            body["quantity"] = quantity
        if quote_qty is not None:
            body["quoteQty"] = quote_qty
        return await self._signed_post("/v4/order", body=body)

    async def _signed_get(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        _retried: bool = False,
    ) -> Any:
        query = sorted_query_string(params)
        headers = signed_headers(
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
            timestamp_ms=self._clock_ms(),
            method="GET",
            path=path,
            query=query,
        )
        request_headers = {
            **headers,
            "accept": "*/*",
            "Content-Type": "application/json",
        }
        url = path if not query else f"{path}?{query}"
        try:
            response = await self._client.get(url, headers=request_headers)
        except httpx.TimeoutException as exc:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                "XT private request timed out.",
            ) from exc
        except httpx.HTTPError as exc:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                "XT private request failed due to a network error.",
            ) from exc

        if response.status_code == 429:
            return await self._handle_rate_limit(
                path, params=params, response=response, retried=_retried
            )

        return self._parse_response(response)

    async def _signed_post(
        self,
        path: str,
        *,
        body: Mapping[str, str],
        _retried: bool = False,
    ) -> Any:
        import json

        body_text = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        headers = signed_headers(
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
            timestamp_ms=self._clock_ms(),
            method="POST",
            path=path,
            query="",
            body=body_text,
        )
        request_headers = {
            **headers,
            "accept": "*/*",
            "Content-Type": "application/json",
        }
        try:
            response = await self._client.post(path, headers=request_headers, content=body_text)
        except httpx.TimeoutException as exc:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                "XT private request timed out.",
            ) from exc
        except httpx.HTTPError as exc:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                "XT private request failed due to a network error.",
            ) from exc

        if response.status_code == 429:
            if _retried:
                raise XtPrivateError(
                    RATE_LIMITED,
                    "XT private rate limit exceeded after one retry.",
                )
            delay = _parse_retry_after(response.headers.get("Retry-After"))
            if delay is None:
                delay = SHORT_BACKOFF_S
            if delay > MAX_RETRY_AFTER_WAIT_S:
                raise XtPrivateError(
                    RATE_LIMITED,
                    "XT private rate limited; Retry-After exceeds the allowed wait bound.",
                )
            await self._sleep(delay)
            return await self._signed_post(path, body=body, _retried=True)

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> Any:
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                f"XT private service returned HTTP {response.status_code} "
                "with a non-JSON body."
                if response.status_code >= 400
                else "Malformed XT private JSON response.",
            ) from exc

        if isinstance(payload, dict) and ("rc" in payload or "mc" in payload):
            return require_success_envelope(payload)

        if response.status_code != 200:
            raise XtPrivateError(
                XT_PRIVATE_UNAVAILABLE,
                f"XT private service returned HTTP {response.status_code}.",
            )
        raise XtPrivateError(
            XT_PRIVATE_UNAVAILABLE,
            "Malformed XT private response envelope.",
        )

    async def _handle_rate_limit(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None,
        response: httpx.Response,
        retried: bool,
    ) -> Any:
        if retried:
            raise XtPrivateError(
                RATE_LIMITED,
                "XT private rate limit exceeded after one retry.",
            )
        delay = _parse_retry_after(response.headers.get("Retry-After"))
        if delay is None:
            delay = SHORT_BACKOFF_S
        if delay > MAX_RETRY_AFTER_WAIT_S:
            raise XtPrivateError(
                RATE_LIMITED,
                "XT private rate limited; Retry-After exceeds the allowed wait bound.",
            )
        await self._sleep(delay)
        return await self._signed_get(path, params=params, _retried=True)
