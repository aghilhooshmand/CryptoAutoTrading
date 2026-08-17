"""Venue-neutral private-account port (Feature 013). No Kraken/XT types."""

from __future__ import annotations

from typing import Protocol

from app.account.models import (
    AccountBalancesResponse,
    AccountOpenOrdersResponse,
    AccountOrderStatusResponse,
)


class PrivateAccountPort(Protocol):
    """Read-only private-account boundary consumed by HTTP/UI.

    Implementations live in venue adapters. Core MUST NOT import Kraken or XT
    payload types through this port. No place/cancel methods in Feature 013.
    """

    async def get_balances(self) -> AccountBalancesResponse: ...

    async def list_open_orders(
        self,
        venue_product_id: str | None = None,
    ) -> AccountOpenOrdersResponse: ...

    async def get_order(self, venue_order_id: str) -> AccountOrderStatusResponse: ...
