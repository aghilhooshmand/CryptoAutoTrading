"""Load Kraken private credentials from environment (never log secret values)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.account.errors import CREDENTIALS_MISSING, AccountPrivateError

ENV_API_KEY = "KRAKEN_API_KEY"
ENV_API_SECRET = "KRAKEN_API_SECRET"


@dataclass(frozen=True)
class KrakenCredentials:
    api_key: str
    api_secret: str


def load_kraken_credentials(
    *,
    environ: dict[str, str] | None = None,
) -> KrakenCredentials:
    """Return credentials or raise credentials_missing (fail closed)."""
    env = environ if environ is not None else os.environ
    key = (env.get(ENV_API_KEY) or "").strip()
    secret = (env.get(ENV_API_SECRET) or "").strip()
    if not key or not secret:
        raise AccountPrivateError(
            CREDENTIALS_MISSING,
            "Kraken private credentials are not configured.",
        )
    return KrakenCredentials(api_key=key, api_secret=secret)
