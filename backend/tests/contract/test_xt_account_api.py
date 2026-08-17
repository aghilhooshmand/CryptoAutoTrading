"""Contract tests for /xt-account (mocked service; no live XT)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.market_data.adapters.base import MarketDataAdapterError
from app.market_data.models import PairStatus, TradingPair
from app.market_data.service import MarketDataService, set_market_data_service
from app.xt_account.credentials import PrivateCredentials
from app.xt_account.errors import (
    AUTHENTICATION_FAILED,
    CREDENTIALS_MISSING,
    ORDER_NOT_FOUND,
    RATE_LIMITED,
    TIMESTAMP_INVALID,
    XT_PRIVATE_UNAVAILABLE,
    XtPrivateError,
)
from app.xt_account.models import (
    RealXtBalance,
    RealXtBalancesResponse,
    RealXtOpenOrdersResponse,
    RealXtOrder,
    RealXtOrderStatusResponse,
)
from app.xt_account.service import XtAccountService, set_xt_account_service


class FakeXtAccountService(XtAccountService):
    def __init__(self, *, fail: XtPrivateError | None = None) -> None:
        super().__init__(
            credentials=PrivateCredentials("test-key", "test-secret"),
        )
        self.fail = fail

    async def get_balances(self) -> RealXtBalancesResponse:
        if self.fail:
            raise self.fail
        return RealXtBalancesResponse(
            retrievedAt="2026-08-16T01:00:00.000Z",
            balances=[
                RealXtBalance(
                    asset="usdt",
                    free="100.5",
                    locked="10",
                    total="110.5",
                )
            ],
        )

    async def list_open_orders(
        self, symbol: str | None = None
    ) -> RealXtOpenOrdersResponse:
        if self.fail:
            raise self.fail
        return RealXtOpenOrdersResponse(
            retrievedAt="2026-08-16T01:00:00.000Z",
            orders=[
                RealXtOrder(
                    orderId="6216559590087220004",
                    symbol="BTC_USDT",
                    side="BUY",
                    orderType="LIMIT",
                    quantity="2",
                    price="40000",
                    executedQty="1.2",
                    status="NEW",
                    updatedAt="2026-08-16T00:55:00.000Z",
                )
            ],
        )

    async def get_order(self, order_id: str) -> RealXtOrderStatusResponse:
        if self.fail:
            raise self.fail
        if order_id == "missing":
            raise XtPrivateError(ORDER_NOT_FOUND, "Order was not found on the XT account.")
        return RealXtOrderStatusResponse(
            retrievedAt="2026-08-16T01:00:00.000Z",
            order=RealXtOrder(
                orderId=order_id,
                symbol="BTC_USDT",
                side="BUY",
                orderType="LIMIT",
                quantity="2",
                price="40000",
                executedQty="2",
                status="FILLED",
                updatedAt="2026-08-16T00:58:00.000Z",
            ),
        )


@pytest.fixture
def client():
    set_xt_account_service(None)
    with TestClient(app) as test_client:
        yield test_client
    set_xt_account_service(None)


def test_credentials_missing_returns_503(client: TestClient) -> None:
    set_xt_account_service(XtAccountService(environ={}))
    for path in ("/xt-account/balances", "/xt-account/open-orders", "/xt-account/orders/1"):
        response = client.get(path)
        assert response.status_code == 503, path
        body = response.json()
        assert body["error"]["code"] == CREDENTIALS_MISSING
        assert "balances" not in body
        assert "orders" not in body
        assert "order" not in body
        assert "test-key" not in response.text
        assert "secret" not in response.text.lower() or "not configured" in response.text.lower()


def test_balances_success_shape(client: TestClient) -> None:
    set_xt_account_service(FakeXtAccountService())
    response = client.get("/xt-account/balances")
    assert response.status_code == 200
    body = response.json()
    assert body["bookProvenance"] == "real_xt"
    assert body["balances"][0]["provenance"] == "real_xt"
    assert body["balances"][0]["asset"] == "usdt"


def test_balances_empty_success(client: TestClient) -> None:
    class Empty(FakeXtAccountService):
        async def get_balances(self) -> RealXtBalancesResponse:
            return RealXtBalancesResponse(
                retrievedAt="2026-08-16T01:00:00.000Z",
                balances=[],
            )

    set_xt_account_service(Empty())
    response = client.get("/xt-account/balances")
    assert response.status_code == 200
    assert response.json()["balances"] == []


def test_open_orders_and_order_status(client: TestClient) -> None:
    set_xt_account_service(FakeXtAccountService())
    open_resp = client.get("/xt-account/open-orders")
    assert open_resp.status_code == 200
    assert open_resp.json()["orders"][0]["orderId"] == "6216559590087220004"

    status_resp = client.get("/xt-account/orders/6216559590087220004")
    assert status_resp.status_code == 200
    assert status_resp.json()["order"]["status"] == "FILLED"

    missing = client.get("/xt-account/orders/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == ORDER_NOT_FOUND


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (AUTHENTICATION_FAILED, 401),
        (TIMESTAMP_INVALID, 401),
        (RATE_LIMITED, 429),
        (XT_PRIVATE_UNAVAILABLE, 502),
        (ORDER_NOT_FOUND, 404),
    ],
)
def test_error_envelopes(client: TestClient, code: str, status: int) -> None:
    set_xt_account_service(
        FakeXtAccountService(fail=XtPrivateError(code, f"fixture {code}"))
    )
    response = client.get("/xt-account/balances")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_no_place_cancel_withdraw_routes(client: TestClient) -> None:
    paths = [
        ("POST", "/xt-account/orders"),
        ("DELETE", "/xt-account/orders/1"),
        ("POST", "/xt-account/withdraw"),
        ("POST", "/xt-account/transfer"),
    ]
    for method, path in paths:
        response = client.request(method, path)
        assert response.status_code in (404, 405), (method, path, response.status_code)


def test_client_has_place_market_order_for_adapter_only() -> None:
    from app.xt_account.client import XtPrivateClient

    assert hasattr(XtPrivateClient, "place_market_order")
    # HTTP surface still must not expose place/cancel/withdraw (see paths above).


def test_public_market_works_without_private_credentials(client: TestClient) -> None:
    """FR-016: Feature 002 remains available without XT_API_*."""

    class FakeAdapter:
        async def list_usdt_pairs(self):
            return [
                TradingPair(
                    symbol="btc_usdt",
                    displayName="BTC/USDT",
                    baseCurrency="btc",
                    quoteCurrency="usdt",
                    status=PairStatus.TRADABLE,
                )
            ]

        async def list_spot_pairs(self):
            return await self.list_usdt_pairs()

        async def get_quote(self, symbol: str):
            raise MarketDataAdapterError("unused")

        async def get_candles(self, *args, **kwargs):
            raise MarketDataAdapterError("unused")

    set_market_data_service(MarketDataService(adapter=FakeAdapter(), venue="xt"))
    set_xt_account_service(XtAccountService(environ={}))
    market = client.get("/market/pairs")
    assert market.status_code == 200
    assert market.json()["pairs"][0]["symbol"] == "btc_usdt"
    private = client.get("/xt-account/balances")
    assert private.status_code == 503
    set_market_data_service(None)
