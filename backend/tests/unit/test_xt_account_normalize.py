"""Unit tests for Real XT balance/order normalization."""

from __future__ import annotations

from app.xt_account.normalize import normalize_balances, normalize_open_orders, normalize_order


def test_omit_zero_zero_balances() -> None:
    result = {
        "assets": [
            {
                "currency": "usdt",
                "availableAmount": "100.5",
                "frozenAmount": "10",
                "totalAmount": "110.5",
            },
            {
                "currency": "btc",
                "availableAmount": "0",
                "frozenAmount": "0",
                "totalAmount": "0",
            },
            {
                "currency": "eth",
                "availableAmount": "0",
                "frozenAmount": "0.01",
                "totalAmount": "0.01",
            },
        ]
    }
    balances = normalize_balances(result)
    assets = {b.asset for b in balances}
    assert assets == {"usdt", "eth"}
    usdt = next(b for b in balances if b.asset == "usdt")
    assert usdt.free == "100.5"
    assert usdt.locked == "10"
    assert usdt.total == "110.5"
    assert usdt.provenance == "real_xt"


def test_empty_balances_success() -> None:
    assert normalize_balances({"assets": []}) == []
    assert normalize_balances({"assets": [
        {"currency": "xt", "availableAmount": 0, "frozenAmount": 0}
    ]}) == []


def test_derive_total_when_missing() -> None:
    balances = normalize_balances(
        {
            "assets": [
                {
                    "currency": "usdt",
                    "availableAmount": "2",
                    "frozenAmount": "3",
                }
            ]
        }
    )
    assert balances[0].total == "5"


def test_normalize_open_orders() -> None:
    orders = normalize_open_orders(
        [
            {
                "symbol": "BTC_USDT",
                "orderId": "6216559590087220004",
                "side": "BUY",
                "type": "LIMIT",
                "origQty": "2",
                "price": "40000",
                "executedQty": "1.2",
                "state": "NEW",
                "updatedTime": 1655958915583,
            }
        ]
    )
    assert len(orders) == 1
    assert orders[0].orderId == "6216559590087220004"
    assert orders[0].status == "NEW"
    assert orders[0].provenance == "real_xt"
    assert orders[0].updatedAt is not None


def test_normalize_order_status() -> None:
    order = normalize_order(
        {
            "symbol": "BTC_USDT",
            "orderId": "1",
            "side": "SELL",
            "type": "MARKET",
            "origQty": "0.1",
            "executedQty": "0.1",
            "state": "FILLED",
            "time": 1655958915583,
        }
    )
    assert order is not None
    assert order.status == "FILLED"
    assert order.side == "SELL"
