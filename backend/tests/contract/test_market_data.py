"""Contract tests for /market endpoints (mocked adapter; no live XT)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.models import (
    CandleInterval,
    Candlestick,
    CandlestickSeries,
    MarketQuote,
    MarketStatus,
    PairStatus,
    TradingPair,
)
from app.market_data.service import MarketDataService, set_market_data_service


class FakeAdapter:
    def __init__(self, *, fail_pairs: bool = False) -> None:
        self.fail_pairs = fail_pairs
        self.pairs = [
            TradingPair(
                symbol="btc_usdt",
                displayName="BTC/USDT",
                baseCurrency="btc",
                quoteCurrency="usdt",
                status=PairStatus.TRADABLE,
            ),
            TradingPair(
                symbol="eth_usdt",
                displayName="ETH/USDT",
                baseCurrency="eth",
                quoteCurrency="usdt",
                status=PairStatus.TRADABLE,
            ),
        ]

    async def list_usdt_pairs(self) -> list[TradingPair]:
        if self.fail_pairs:
            raise MarketDataAdapterError("Unable to retrieve XT Spot pairs")
        return list(self.pairs)

    async def list_spot_pairs(self) -> list[TradingPair]:
        return await self.list_usdt_pairs()

    async def get_quote(self, symbol: str) -> MarketQuote:
        symbol = symbol.lower()
        if symbol not in {p.symbol for p in self.pairs}:
            raise UnsupportedSymbolError(symbol)
        now = datetime(2026, 8, 9, 16, 0, 0, tzinfo=timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65220.00",
            changeAbsolute="129.99",
            changePercent="0.19",
            high24h="65300.00",
            low24h="64730.08",
            volumeBase="1762.90919",
            volumeQuote="114569255.8349815",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    async def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        symbol = symbol.lower()
        if symbol not in {p.symbol for p in self.pairs}:
            raise UnsupportedSymbolError(symbol)
        now = datetime(2026, 8, 9, 16, 0, 1, tzinfo=timezone.utc)
        return CandlestickSeries(
            symbol=symbol,
            interval=interval,
            candles=[
                Candlestick(
                    openTime=1786287600000,
                    open="65263.99",
                    high="65264.00",
                    low="65215.11",
                    close="65228.68",
                    volumeBase="109.08285",
                    volumeQuote="7116784.4149678",
                )
            ],
            source="XT",
            retrievedAt=now,
        )


@pytest.fixture(autouse=True)
def _install_fake_service() -> None:
    set_market_data_service(MarketDataService(FakeAdapter(), venue="xt"))
    yield
    set_market_data_service(None)


client = TestClient(app)


def test_pairs_returns_usdt_only_normalized() -> None:
    response = client.get("/market/pairs")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "XT"
    assert all(p["quoteCurrency"] == "usdt" for p in body["pairs"])
    assert {p["symbol"] for p in body["pairs"]} == {"btc_usdt", "eth_usdt"}


def test_pairs_failure_returns_error_without_invented_pairs() -> None:
    set_market_data_service(MarketDataService(FakeAdapter(fail_pairs=True), venue="xt"))
    response = client.get("/market/pairs")
    assert response.status_code == 502
    body = response.json()
    assert "error" in body
    assert "pairs" not in body


def test_quote_decimal_strings_and_percent_points() -> None:
    response = client.get("/market/quote", params={"symbol": "btc_usdt"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "XT"
    assert body["lastPrice"] == "65220.00"
    assert body["changePercent"] == "0.19"
    assert isinstance(body["lastPrice"], str)
    assert isinstance(body["changePercent"], str)
    assert body["status"] == "fresh"


def test_quote_unsupported_symbol() -> None:
    response = client.get("/market/quote", params={"symbol": "nope_usdt"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unsupported"


def test_candles_allowed_interval_decimal_ohlc() -> None:
    response = client.get(
        "/market/candles",
        params={"symbol": "btc_usdt", "interval": "1h", "limit": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == "1h"
    candle = body["candles"][0]
    assert isinstance(candle["open"], str)
    assert isinstance(candle["close"], str)
    assert isinstance(candle["openTime"], int)


@pytest.mark.parametrize("interval", ["1m", "5m"])
def test_candles_accepts_short_intervals(interval: str) -> None:
    response = client.get(
        "/market/candles",
        params={"symbol": "btc_usdt", "interval": interval, "limit": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == interval
    assert len(body["candles"]) >= 1


def test_candles_invalid_interval() -> None:
    response = client.get(
        "/market/candles",
        params={"symbol": "btc_usdt", "interval": "3m"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_interval"


class FakeKrakenAdapter:
    def __init__(self) -> None:
        self.pairs = [
            TradingPair(
                symbol="BTC/EUR",
                displayName="BTC/EUR",
                baseCurrency="btc",
                quoteCurrency="eur",
                status=PairStatus.TRADABLE,
                venue="kraken",
                venueProductId="XXBTZEUR",
                canonicalSymbol="BTC/EUR",
                baseAsset="BTC",
                quoteAsset="EUR",
            )
        ]

    async def list_spot_pairs(self) -> list[TradingPair]:
        return list(self.pairs)

    async def get_quote(self, symbol: str) -> MarketQuote:
        now = datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc)
        return MarketQuote(
            symbol="BTC/EUR",
            lastPrice="91234.5",
            changePercent="1.37",
            source="kraken",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    async def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        now = datetime(2026, 8, 17, 12, 0, 1, tzinfo=timezone.utc)
        return CandlestickSeries(
            symbol="BTC/EUR",
            interval=interval,
            candles=[
                Candlestick(
                    openTime=1786287600000,
                    open="91000.0",
                    high="92000.0",
                    low="90000.0",
                    close="91234.5",
                )
            ],
            source="kraken",
            retrievedAt=now,
        )


def test_pairs_default_kraken_source() -> None:
    set_market_data_service(MarketDataService(FakeKrakenAdapter(), venue="kraken"))
    response = client.get("/market/pairs")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "kraken"
    assert body["pairs"][0]["canonicalSymbol"] == "BTC/EUR"
    assert body["pairs"][0]["venueProductId"] == "XXBTZEUR"


def test_xt_venue_query_stays_xt() -> None:
    set_market_data_service(MarketDataService(FakeAdapter(), venue="xt"))
    response = client.get("/market/pairs", params={"venue": "xt"})
    assert response.status_code == 200
    assert response.json()["source"] == "XT"


def test_factory_default_venue_is_kraken() -> None:
    set_market_data_service(None)
    assert MarketDataService().venue == "kraken"

