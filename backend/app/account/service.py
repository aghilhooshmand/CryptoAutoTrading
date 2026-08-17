"""Orchestration for Real Kraken account reads (Feature 013 amendment)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.account.credentials import KrakenCredentials, load_kraken_credentials
from app.account.errors import ORDER_NOT_FOUND, AccountPrivateError
from app.account.kraken_private import KrakenPrivateClient
from app.account.models import (
    AccountBalancesResponse,
    AccountOpenOrdersResponse,
    AccountOrderStatusResponse,
)
from app.account.normalize import (
    normalize_balances,
    normalize_open_orders,
    normalize_query_orders,
)
from app.market_data.identity import VENUE_KRAKEN


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class KrakenAccountService:
    """Credential-gated read orchestration; injectable client for tests."""

    def __init__(
        self,
        *,
        credentials: KrakenCredentials | None = None,
        client: KrakenPrivateClient | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self._environ = environ
        self._credentials = credentials
        self._client = client

    def _require_credentials(self) -> KrakenCredentials:
        if self._credentials is not None:
            return self._credentials
        return load_kraken_credentials(environ=self._environ)

    def _require_client(self) -> KrakenPrivateClient:
        if self._client is not None:
            return self._client
        creds = self._require_credentials()
        self._credentials = creds
        self._client = KrakenPrivateClient(creds)
        return self._client

    async def get_balances(self) -> AccountBalancesResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.get_balances()
        return AccountBalancesResponse(
            venue=VENUE_KRAKEN,
            retrievedAt=_utc_now_iso(),
            balances=normalize_balances(result),
        )

    async def list_open_orders(
        self,
        venue_product_id: str | None = None,
    ) -> AccountOpenOrdersResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.list_open_orders(venue_product_id=venue_product_id)
        return AccountOpenOrdersResponse(
            venue=VENUE_KRAKEN,
            retrievedAt=_utc_now_iso(),
            orders=normalize_open_orders(result, venue_product_id=venue_product_id),
        )

    async def get_order(self, venue_order_id: str) -> AccountOrderStatusResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.get_order(venue_order_id)
        orders = normalize_query_orders(result)
        if not orders:
            raise AccountPrivateError(
                ORDER_NOT_FOUND,
                "Order was not found on the Kraken account.",
            )
        return AccountOrderStatusResponse(
            venue=VENUE_KRAKEN,
            retrievedAt=_utc_now_iso(),
            order=orders[0],
        )


_service: Optional[KrakenAccountService] = None


def get_account_service() -> KrakenAccountService:
    global _service
    if _service is None:
        _service = KrakenAccountService()
    return _service


def set_account_service(service: KrakenAccountService | None) -> None:
    global _service
    _service = service
