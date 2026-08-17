"""Kraken public adapter mapping from recorded fixtures (no live HTTP)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.market_data.adapters.kraken_public import (
    map_asset_pair,
    map_ohlc_result,
    map_ticker_result,
)
from app.market_data.identity import pick_default_kraken_pair
from app.market_data.models import CandleInterval


_ASSET_PAIRS = {
    "XXBTZEUR": {
        "altname": "XBTEUR",
        "wsname": "XBT/EUR",
        "base": "XXBT",
        "quote": "ZEUR",
        "status": "online",
    },
    "XXBTZUSD": {
        "altname": "XBTUSD",
        "wsname": "XBT/USD",
        "base": "XXBT",
        "quote": "ZUSD",
        "status": "online",
    },
    "XBTUSDT": {
        "altname": "XBTUSDT",
        "wsname": "XBT/USDT",
        "base": "XXBT",
        "quote": "USDT",
        "status": "online",
    },
}

_TICKER = {
    "c": ["91234.5", "0.01"],
    "o": "90000.0",
    "h": ["92000.0", "91500.0"],
    "l": ["89000.0", "89500.0"],
    "v": ["12.5", "40.0"],
}

_OHLC = [
    [1700000000, "100.0", "101.0", "99.0", "100.5", "100.2", "15.0", 8],
    [1700003600, "100.5", "102.0", "100.0", "101.5", "101.0", "20.0", 10],
]


def test_map_asset_pair_normalizes_xbt_to_btc() -> None:
    pair = map_asset_pair("XXBTZEUR", _ASSET_PAIRS["XXBTZEUR"])
    assert pair is not None
    assert pair.venue == "kraken"
    assert pair.canonicalSymbol == "BTC/EUR"
    assert pair.venueProductId == "XXBTZEUR"
    assert pair.baseAsset == "BTC"
    assert pair.quoteAsset == "EUR"
    assert pair.symbol == "BTC/EUR"


def test_default_kraken_pair_prefers_btc_eur() -> None:
    pairs = [map_asset_pair(k, v) for k, v in _ASSET_PAIRS.items()]
    picked = pick_default_kraken_pair([p for p in pairs if p is not None])
    assert picked is not None
    assert picked.canonicalSymbol == "BTC/EUR"


def test_map_ticker_decimal_strings_and_percent_points() -> None:
    now = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    quote = map_ticker_result(
        "XXBTZEUR",
        _TICKER,
        retrieved_at=now,
        canonical_symbol="BTC/EUR",
    )
    assert quote.symbol == "BTC/EUR"
    assert quote.lastPrice == "91234.5"
    assert quote.source == "kraken"
    assert isinstance(quote.changePercent, str)
    # (91234.5 - 90000) / 90000 * 100 = 1.3716...
    assert quote.changePercent.startswith("1.37")


def test_map_ohlc_unix_seconds_to_ms() -> None:
    now = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    series = map_ohlc_result(
        _OHLC,
        canonical_symbol="BTC/EUR",
        interval=CandleInterval.H1,
        retrieved_at=now,
    )
    assert series.symbol == "BTC/EUR"
    assert series.source == "kraken"
    assert series.candles[0].openTime == 1700000000 * 1000
    assert series.candles[0].open == "100.0"
    assert series.candles[1].close == "101.5"
