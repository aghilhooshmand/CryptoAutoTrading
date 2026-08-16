"""Unit tests for XT private request signing."""

from __future__ import annotations

from app.xt_account.signing import (
    data_signing_string,
    header_signing_string,
    signed_headers,
    sign_payload,
)


def test_deterministic_get_balances_signature() -> None:
    appkey = "3976eb88-76d0-4f6e-a6b2-a57980770085"
    secret = "bc6630d0231fda5cd98794f52c4998659beda290"
    timestamp = "1641446237201"
    headers = signed_headers(
        api_key=appkey,
        api_secret=secret,
        timestamp_ms=timestamp,
        method="GET",
        path="/v4/balances",
    )
    assert headers["validate-algorithms"] == "HmacSHA256"
    assert headers["validate-appkey"] == appkey
    assert headers["validate-recvwindow"] == "5000"
    assert headers["validate-timestamp"] == timestamp
    assert headers["validate-signature"] == (
        "6f65f1289568e3ce07cfa8b1b9664e897e19fcaedc063aac74e4e4e510ab006b"
    )


def test_deterministic_get_open_orders_with_query() -> None:
    appkey = "3976eb88-76d0-4f6e-a6b2-a57980770085"
    secret = "bc6630d0231fda5cd98794f52c4998659beda290"
    headers = signed_headers(
        api_key=appkey,
        api_secret=secret,
        timestamp_ms="1641446237201",
        method="GET",
        path="/v4/open-order",
        query="symbol=btc_usdt",
    )
    assert headers["validate-signature"] == (
        "f72eb98d8f49eea1e29e4a0e8f50ebc15e83c88e0efb9f9380bf908f22a75832"
    )


def test_header_and_data_parts_compose() -> None:
    x = header_signing_string(
        {
            "validate-algorithms": "HmacSHA256",
            "validate-appkey": "k",
            "validate-recvwindow": "5000",
            "validate-timestamp": "1",
        }
    )
    y = data_signing_string(method="GET", path="/v4/balances")
    assert x.startswith("validate-algorithms=")
    assert y == "#GET#/v4/balances"
    assert len(sign_payload(secret="s", original=x + y)) == 64
