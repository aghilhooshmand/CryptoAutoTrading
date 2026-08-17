"""Kraken private REST signing — adapter-only (Feature 013)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import urllib.parse
from collections.abc import Mapping

from app.account.errors import CREDENTIALS_MISSING, AccountPrivateError


def encode_postdata(data: Mapping[str, str]) -> str:
    """Canonical application/x-www-form-urlencoded body used for both sign and POST."""
    return urllib.parse.urlencode(data)


def sign_kraken_request(
    *,
    url_path: str,
    postdata: str,
    nonce: str,
    secret_b64: str,
) -> str:
    """Return API-Sign: Base64(HMAC-SHA512(path + SHA256(nonce + POST data)))."""
    try:
        secret = base64.b64decode(secret_b64)
    except (binascii.Error, ValueError) as exc:
        raise AccountPrivateError(
            CREDENTIALS_MISSING,
            "Kraken private credentials are not configured.",
        ) from exc
    if not secret:
        raise AccountPrivateError(
            CREDENTIALS_MISSING,
            "Kraken private credentials are not configured.",
        )
    encoded = (nonce + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(secret, message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


def signed_headers(
    *,
    api_key: str,
    api_secret: str,
    url_path: str,
    postdata: str,
    nonce: str,
) -> dict[str, str]:
    signature = sign_kraken_request(
        url_path=url_path,
        postdata=postdata,
        nonce=nonce,
        secret_b64=api_secret,
    )
    return {
        "API-Key": api_key,
        "API-Sign": signature,
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    }
