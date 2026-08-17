"""Unit tests for Kraken private balance/order normalization."""

from __future__ import annotations

from app.account.normalize import (
    normalize_balances,
    normalize_open_orders,
    normalize_query_orders,
)


def test_balance_ex_maps_hold_trade_and_omits_zero_zero() -> None:
    balances = normalize_balances(
        {
            "ZEUR": {"balance": "110.5", "hold_trade": "10"},
            "XXBT": {"balance": "0", "hold_trade": "0"},
            "XETH": {"balance": "0", "hold_trade": "0.01"},
        }
    )
    assets = {row.asset for row in balances}
    assert assets == {"EUR", "ETH"}
    eur = next(row for row in balances if row.asset == "EUR")
    assert eur.free == "100.5"
    assert eur.locked == "10"
    assert eur.total == "110.5"
    assert eur.venue == "kraken"
    eth = next(row for row in balances if row.asset == "ETH")
    assert eth.free == "0"
    assert eth.locked == "0.01"


def test_plain_balance_does_not_invent_locked() -> None:
    balances = normalize_balances({"ZEUR": "25.0", "XXBT": "0"})
    assert len(balances) == 1
    assert balances[0].asset == "EUR"
    assert balances[0].free == "25.0"
    assert balances[0].locked is None
    assert balances[0].total == "25.0"


def test_empty_balances_success() -> None:
    assert normalize_balances({}) == []
    assert normalize_balances({"ZEUR": {"balance": "0", "hold_trade": "0"}}) == []


def test_normalize_open_orders() -> None:
    orders = normalize_open_orders(
        {
            "open": {
                "O7MN22-ZCX7J-TGLQHD": {
                    "status": "open",
                    "opentm": 1692272100.0,
                    "vol": "0.01",
                    "vol_exec": "0",
                    "descr": {
                        "pair": "XXBTZEUR",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "50000",
                    },
                }
            }
        }
    )
    assert len(orders) == 1
    assert orders[0].venueOrderId == "O7MN22-ZCX7J-TGLQHD"
    assert orders[0].venueProductId == "XXBTZEUR"
    assert orders[0].side == "BUY"
    assert orders[0].venue == "kraken"


def test_open_orders_filter_by_product() -> None:
    result = {
        "open": {
            "AAA": {
                "status": "open",
                "descr": {"pair": "XXBTZEUR", "type": "buy", "ordertype": "limit"},
            },
            "BBB": {
                "status": "open",
                "descr": {"pair": "XETHZEUR", "type": "sell", "ordertype": "limit"},
            },
        }
    }
    orders = normalize_open_orders(result, venue_product_id="xxbtzeur")
    assert [row.venueOrderId for row in orders] == ["AAA"]


def test_query_orders_empty() -> None:
    assert normalize_query_orders({}) == []
