"""Contract tests for /account (mocked service; no live Kraken)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.account.credentials import KrakenCredentials
from app.account.errors import (
    AUTHENTICATION_FAILED,
    CREDENTIALS_MISSING,
    ORDER_NOT_FOUND,
    RATE_LIMITED,
    TIMESTAMP_INVALID,
    VENUE_PRIVATE_UNAVAILABLE,
    AccountPrivateError,
)
from app.account.models import (
    AccountBalancesResponse,
    AccountOpenOrdersResponse,
    AccountOrderStatusResponse,
    VenueBalance,
    VenueOrder,
)
from app.account.service import KrakenAccountService, set_account_service
from app.main import app
from app.market_data.adapters.base import MarketDataAdapterError
from app.market_data.models import PairStatus, TradingPair
from app.market_data.service import MarketDataService, set_market_data_service


class FakeAccountService(KrakenAccountService):
    def __init__(self, *, fail: AccountPrivateError | None = None) -> None:
        super().__init__(
            credentials=KrakenCredentials("test-key", "test-secret"),
        )
        self.fail = fail

    async def get_balances(self) -> AccountBalancesResponse:
        if self.fail:
            raise self.fail
        return AccountBalancesResponse(
            retrievedAt="2026-08-17T20:00:00.000Z",
            balances=[
                VenueBalance(
                    asset="EUR",
                    free="100.5",
                    locked="10",
                    total="110.5",
                )
            ],
        )

    async def list_open_orders(
        self, venue_product_id: str | None = None
    ) -> AccountOpenOrdersResponse:
        if self.fail:
            raise self.fail
        return AccountOpenOrdersResponse(
            retrievedAt="2026-08-17T20:00:00.000Z",
            orders=[
                VenueOrder(
                    venueOrderId="O7MN22-ZCX7J-TGLQHD",
                    venueProductId="XXBTZEUR",
                    side="BUY",
                    orderType="limit",
                    quantity="0.01",
                    price="50000",
                    executedQty="0",
                    status="open",
                    updatedAt="2026-08-17T19:55:00.000Z",
                )
            ],
        )

    async def get_order(self, venue_order_id: str) -> AccountOrderStatusResponse:
        if self.fail:
            raise self.fail
        if venue_order_id == "missing":
            raise AccountPrivateError(
                ORDER_NOT_FOUND,
                "Order was not found on the Kraken account.",
            )
        return AccountOrderStatusResponse(
            retrievedAt="2026-08-17T20:00:00.000Z",
            order=VenueOrder(
                venueOrderId=venue_order_id,
                venueProductId="XXBTZEUR",
                side="BUY",
                orderType="limit",
                quantity="0.01",
                price="50000",
                executedQty="0.01",
                status="closed",
                updatedAt="2026-08-17T19:58:00.000Z",
            ),
        )


@pytest.fixture
def client():
    set_account_service(None)
    with TestClient(app) as test_client:
        yield test_client
    set_account_service(None)


def test_credentials_missing_returns_503(client: TestClient) -> None:
    set_account_service(KrakenAccountService(environ={}))
    for path in ("/account/balances", "/account/open-orders", "/account/orders/1"):
        response = client.get(path)
        assert response.status_code == 503, path
        body = response.json()
        assert body["error"]["code"] == CREDENTIALS_MISSING
        assert "balances" not in body
        assert "orders" not in body
        assert "order" not in body
        assert "test-key" not in response.text


def test_balances_success_shape(client: TestClient) -> None:
    set_account_service(FakeAccountService())
    response = client.get("/account/balances")
    assert response.status_code == 200
    body = response.json()
    assert body["venue"] == "kraken"
    assert body["balances"][0]["venue"] == "kraken"
    assert body["balances"][0]["asset"] == "EUR"
    assert body["balances"][0]["locked"] == "10"


def test_open_orders_and_order_status(client: TestClient) -> None:
    set_account_service(FakeAccountService())
    open_resp = client.get("/account/open-orders")
    assert open_resp.status_code == 200
    assert open_resp.json()["orders"][0]["venueOrderId"] == "O7MN22-ZCX7J-TGLQHD"

    status_resp = client.get("/account/orders/O7MN22-ZCX7J-TGLQHD")
    assert status_resp.status_code == 200
    assert status_resp.json()["order"]["status"] == "closed"

    missing = client.get("/account/orders/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == ORDER_NOT_FOUND


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (AUTHENTICATION_FAILED, 401),
        (TIMESTAMP_INVALID, 401),
        (RATE_LIMITED, 429),
        (VENUE_PRIVATE_UNAVAILABLE, 502),
        (ORDER_NOT_FOUND, 404),
    ],
)
def test_error_envelopes(client: TestClient, code: str, status: int) -> None:
    set_account_service(
        FakeAccountService(fail=AccountPrivateError(code, f"fixture {code}"))
    )
    response = client.get("/account/balances")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_no_place_cancel_withdraw_routes(client: TestClient) -> None:
    paths = [
        ("POST", "/account/orders"),
        ("DELETE", "/account/orders/1"),
        ("POST", "/account/withdraw"),
        ("POST", "/account/transfer"),
        ("POST", "/0/private/AddOrder"),
    ]
    for method, path in paths:
        response = client.request(method, path)
        assert response.status_code in (404, 405), (method, path, response.status_code)


def test_public_market_works_without_kraken_private_credentials(
    client: TestClient,
) -> None:
    class FakeAdapter:
        async def list_spot_pairs(self):
            return [
                TradingPair(
                    symbol="BTC/EUR",
                    displayName="BTC/EUR",
                    baseCurrency="BTC",
                    quoteCurrency="EUR",
                    status=PairStatus.TRADABLE,
                    venue="kraken",
                    venueProductId="XXBTZEUR",
                    canonicalSymbol="BTC/EUR",
                    baseAsset="BTC",
                    quoteAsset="EUR",
                )
            ]

        async def get_quote(self, symbol: str):
            raise MarketDataAdapterError("unused")

        async def get_candles(self, *args, **kwargs):
            raise MarketDataAdapterError("unused")

    set_market_data_service(MarketDataService(adapter=FakeAdapter(), venue="kraken"))
    set_account_service(KrakenAccountService(environ={}))
    market = client.get("/market/pairs")
    assert market.status_code == 200
    assert market.json()["pairs"][0]["symbol"] == "BTC/EUR"
    private = client.get("/account/balances")
    assert private.status_code == 503
    set_market_data_service(None)
