"""Unit tests for XT Spot adapter mapping (no live network)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.market_data.adapters.base import MarketDataAdapterError
from app.market_data.adapters.xt_spot import (
    map_kline_rows,
    map_symbol_row,
    map_ticker_row,
    ratio_to_percent_points,
)
from app.market_data.models import CandleInterval


def test_ratio_to_percent_points() -> None:
    assert ratio_to_percent_points("0.0235") == "2.35"
    assert ratio_to_percent_points("0.0019") == "0.19"
    assert ratio_to_percent_points(None) is None


def test_map_symbol_row_filters_usdt_tradable() -> None:
    row = {
        "symbol": "btc_usdt",
        "displayName": "BTC/USDT",
        "baseCurrency": "btc",
        "quoteCurrency": "usdt",
        "state": "ONLINE",
        "tradingEnabled": True,
        "openapiEnabled": True,
    }
    pair = map_symbol_row(row)
    assert pair is not None
    assert pair.symbol == "btc_usdt"
    assert pair.quoteCurrency == "usdt"

    eth_btc = {**row, "symbol": "eth_btc", "quoteCurrency": "btc"}
    assert map_symbol_row(eth_btc) is None

    offline = {**row, "state": "OFFLINE"}
    assert map_symbol_row(offline) is None


def test_map_ticker_row_decimal_strings_and_percent_points() -> None:
    retrieved = datetime(2026, 8, 9, 16, 0, 1, tzinfo=timezone.utc)
    quote = map_ticker_row(
        {
            "s": "btc_usdt",
            "t": 1723219200000,
            "c": "65220.00",
            "cv": "129.99",
            "cr": "0.0019",
            "h": "65300.00",
            "l": "64730.08",
            "q": "1762.90919",
            "v": "114569255.8349815",
        },
        retrieved_at=retrieved,
    )
    assert quote.lastPrice == "65220.00"
    assert quote.changePercent == "0.19"
    assert quote.changeAbsolute == "129.99"
    assert quote.source == "XT"
    assert quote.status.value == "fresh"
    assert isinstance(quote.lastPrice, str)


def test_map_ticker_row_rejects_missing_price() -> None:
    retrieved = datetime(2026, 8, 9, 16, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(MarketDataAdapterError):
        map_ticker_row({"s": "btc_usdt", "t": 1}, retrieved_at=retrieved)


def test_map_kline_rows_skips_incomplete_bars() -> None:
    retrieved = datetime(2026, 8, 9, 16, 0, 1, tzinfo=timezone.utc)
    series = map_kline_rows(
        [
            {
                "t": 1000,
                "o": "1",
                "h": "2",
                "l": "0.5",
                "c": "1.5",
                "q": "10",
                "v": "20",
            },
            {"t": 2000, "o": "1"},  # incomplete — skip
        ],
        symbol="btc_usdt",
        interval=CandleInterval.H1,
        retrieved_at=retrieved,
    )
    assert len(series.candles) == 1
    assert series.candles[0].open == "1"
    assert series.interval == CandleInterval.H1
