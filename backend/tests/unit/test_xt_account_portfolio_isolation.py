"""Simulation Portfolio isolation from Real XT account reads."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.xt_account.credentials import PrivateCredentials
from app.xt_account.models import RealXtBalancesResponse
from app.xt_account.service import XtAccountService


def test_balance_read_does_not_touch_portfolio_apply() -> None:
    class StubClient:
        async def get_balances(self):
            return {
                "assets": [
                    {
                        "currency": "usdt",
                        "availableAmount": "10",
                        "frozenAmount": "0",
                        "totalAmount": "10",
                    }
                ]
            }

    async def _run() -> None:
        with pytest.MonkeyPatch.context() as mp:
            apply = MagicMock()
            mp.setattr("app.portfolio.service.try_apply_simulation_fill", apply)
            service = XtAccountService(
                credentials=PrivateCredentials("k", "s"),
                client=StubClient(),  # type: ignore[arg-type]
            )
            result = await service.get_balances()
            assert isinstance(result, RealXtBalancesResponse)
            assert result.balances[0].asset == "usdt"
            apply.assert_not_called()

    asyncio.run(_run())


def test_balance_read_does_not_call_portfolio_repository_writes() -> None:
    class StubClient:
        async def get_balances(self):
            return {"assets": []}

    async def _run() -> None:
        repo_writes = MagicMock()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.portfolio.repository.set_funding",
                repo_writes,
                raising=False,
            )
            service = XtAccountService(
                credentials=PrivateCredentials("k", "s"),
                client=StubClient(),  # type: ignore[arg-type]
            )
            result = await service.get_balances()
            assert result.balances == []
            assert result.bookProvenance == "real_xt"
            repo_writes.assert_not_called()

    asyncio.run(_run())
