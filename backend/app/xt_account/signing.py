"""XT Spot v4 private request signing (HMAC-SHA256)."""

from __future__ import annotations

import hashlib
import hmac
from typing import Mapping

DEFAULT_RECV_WINDOW_MS = "5000"
ALGORITHM = "HmacSHA256"


def build_validate_headers(
    *,
    api_key: str,
    timestamp_ms: str,
    recv_window: str = DEFAULT_RECV_WINDOW_MS,
) -> dict[str, str]:
    """Headers used for signing (without signature)."""
    return {
        "validate-algorithms": ALGORITHM,
        "validate-appkey": api_key,
        "validate-recvwindow": recv_window,
        "validate-timestamp": timestamp_ms,
    }


def header_signing_string(headers: Mapping[str, str]) -> str:
    """Build X = sorted validate-* key=value joined by &."""
    pairs = [
        (k, v)
        for k, v in headers.items()
        if k.startswith("validate-") and k != "validate-signature"
    ]
    pairs.sort(key=lambda item: item[0])
    return "&".join(f"{k}={v}" for k, v in pairs)


def data_signing_string(
    *,
    method: str,
    path: str,
    query: str = "",
    body: str = "",
) -> str:
    """Build Y = #METHOD#path[#query][#body] per XT signSteps."""
    parts = ["", method.upper(), path]
    if query:
        parts.append(query)
    if body:
        parts.append(body)
    return "#".join(parts)


def sign_payload(*, secret: str, original: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        original.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def signed_headers(
    *,
    api_key: str,
    api_secret: str,
    timestamp_ms: str,
    method: str,
    path: str,
    query: str = "",
    body: str = "",
    recv_window: str = DEFAULT_RECV_WINDOW_MS,
) -> dict[str, str]:
    """Full validate-* headers including signature."""
    headers = build_validate_headers(
        api_key=api_key,
        timestamp_ms=timestamp_ms,
        recv_window=recv_window,
    )
    x = header_signing_string(headers)
    y = data_signing_string(method=method, path=path, query=query, body=body)
    signature = sign_payload(secret=api_secret, original=x + y)
    headers["validate-signature"] = signature
    return headers


def sorted_query_string(params: Mapping[str, str] | None) -> str:
    """Lexicographically sorted key=value&... for signing and request."""
    if not params:
        return ""
    items = [(str(k), str(v)) for k, v in params.items() if v is not None]
    items.sort(key=lambda item: item[0])
    return "&".join(f"{k}={v}" for k, v in items)
