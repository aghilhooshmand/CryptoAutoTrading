"""Unit tests for Kraken private request signing (no live keys)."""

from __future__ import annotations

from app.account.signing import encode_postdata, sign_kraken_request, signed_headers

# Documented dummy secret (not a live key). Signature is a fixed vector.
_SECRET = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3o5TWMw="
_NONCE = "1616492376594"


def test_deterministic_balance_signature() -> None:
    postdata = encode_postdata({"nonce": _NONCE})
    assert postdata == "nonce=1616492376594"
    signature = sign_kraken_request(
        url_path="/0/private/Balance",
        postdata=postdata,
        nonce=_NONCE,
        secret_b64=_SECRET,
    )
    assert signature == (
        "IWgjgg1NHVMQoJ6BhgTldBb/h8sYktHSRDMtGuYEE/nL9TIYyc62BMc4Aw5YmQ5wvyCo7scROeybCZ8QBb8wmw=="
    )


def test_deterministic_query_orders_signature() -> None:
    postdata = encode_postdata({"nonce": _NONCE, "txid": "O7MN22-ZCX7J-TGLQHD"})
    assert postdata == "nonce=1616492376594&txid=O7MN22-ZCX7J-TGLQHD"
    signature = sign_kraken_request(
        url_path="/0/private/QueryOrders",
        postdata=postdata,
        nonce=_NONCE,
        secret_b64=_SECRET,
    )
    assert signature == (
        "PAooaPRbMz9luPWdiCQsEGfzGv9jBJ74AYqypoqAniCWRCp0GZx9W3HdrZkPkxBUDDK5kGD4fcvu/Cfl2dwHgg=="
    )


def test_signed_headers_do_not_include_secret() -> None:
    postdata = encode_postdata({"nonce": _NONCE})
    headers = signed_headers(
        api_key="public-key",
        api_secret=_SECRET,
        url_path="/0/private/Balance",
        postdata=postdata,
        nonce=_NONCE,
    )
    assert headers["API-Key"] == "public-key"
    assert "API-Sign" in headers
    assert _SECRET not in headers["API-Sign"]
    assert _SECRET not in "".join(headers.values())
