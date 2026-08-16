"""Orchestration for Real XT account reads (Feature 013)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.xt_account.client import XtPrivateClient
from app.xt_account.credentials import PrivateCredentials, load_credentials
from app.xt_account.errors import ORDER_NOT_FOUND, XtPrivateError
from app.xt_account.models import (
    RealXtBalancesResponse,
    RealXtOpenOrdersResponse,
    RealXtOrderStatusResponse,
)
from app.xt_account.normalize import (
    normalize_balances,
    normalize_open_orders,
    normalize_order,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class XtAccountService:
    """Credential-gated read orchestration; injectable client for tests."""

    def __init__(
        self,
        *,
        credentials: PrivateCredentials | None = None,
        client: XtPrivateClient | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self._environ = environ
        self._credentials = credentials
        self._client = client

    def _require_credentials(self) -> PrivateCredentials:
        if self._credentials is not None:
            return self._credentials
        # Fail closed before any network use
        return load_credentials(environ=self._environ)

    def _require_client(self) -> XtPrivateClient:
        if self._client is not None:
            return self._client
        creds = self._require_credentials()
        self._credentials = creds
        self._client = XtPrivateClient(creds)
        return self._client

    async def get_balances(self) -> RealXtBalancesResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.get_balances()
        return RealXtBalancesResponse(
            retrievedAt=_utc_now_iso(),
            balances=normalize_balances(result),
        )

    async def list_open_orders(
        self, symbol: str | None = None
    ) -> RealXtOpenOrdersResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.list_open_orders(symbol=symbol)
        return RealXtOpenOrdersResponse(
            retrievedAt=_utc_now_iso(),
            orders=normalize_open_orders(result),
        )

    async def get_order(self, order_id: str) -> RealXtOrderStatusResponse:
        self._require_credentials()
        client = self._require_client()
        result = await client.get_order(order_id)
        order = normalize_order(result)
        if order is None:
            raise XtPrivateError(
                ORDER_NOT_FOUND,
                "Order was not found on the XT account.",
            )
        return RealXtOrderStatusResponse(
            retrievedAt=_utc_now_iso(),
            order=order,
        )


_service: Optional[XtAccountService] = None


def get_xt_account_service() -> XtAccountService:
    global _service
    if _service is None:
        _service = XtAccountService()
    return _service


def set_xt_account_service(service: XtAccountService | None) -> None:
    global _service
    _service = service
