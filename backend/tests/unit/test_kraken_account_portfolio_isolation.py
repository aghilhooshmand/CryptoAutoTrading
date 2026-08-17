"""Simulation Portfolio isolation from Real Kraken account reads."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.account.credentials import KrakenCredentials
from app.account.models import AccountBalancesResponse
from app.account.service import KrakenAccountService


def test_balance_read_does_not_touch_portfolio_apply() -> None:
    class StubClient:
        async def get_balances(self):
            return {"ZEUR": {"balance": "10", "hold_trade": "0"}}

        async def list_open_orders(self, venue_product_id: str | None = None):
            return {"open": {}}

        async def get_order(self, venue_order_id: str):
            return {}

    async def _run() -> None:
        with pytest.MonkeyPatch.context() as mp:
            apply = MagicMock()
            mp.setattr("app.portfolio.service.try_apply_simulation_fill", apply)
            service = KrakenAccountService(
                credentials=KrakenCredentials("k", "s"),
                client=StubClient(),  # type: ignore[arg-type]
            )
            result = await service.get_balances()
            assert isinstance(result, AccountBalancesResponse)
            assert result.venue == "kraken"
            assert result.balances[0].asset == "EUR"
            apply.assert_not_called()

    asyncio.run(_run())


def test_balance_read_does_not_call_portfolio_repository_writes() -> None:
    class StubClient:
        async def get_balances(self):
            return {}

    async def _run() -> None:
        repo_writes = MagicMock()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.portfolio.repository.set_funding",
                repo_writes,
                raising=False,
            )
            service = KrakenAccountService(
                credentials=KrakenCredentials("k", "s"),
                client=StubClient(),  # type: ignore[arg-type]
            )
            result = await service.get_balances()
            assert result.balances == []
            assert result.venue == "kraken"
            repo_writes.assert_not_called()

    asyncio.run(_run())
