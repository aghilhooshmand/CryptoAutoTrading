"""Load XT private credentials from environment (never log secret values)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.xt_account.errors import CREDENTIALS_MISSING, XtPrivateError

ENV_API_KEY = "XT_API_KEY"
ENV_API_SECRET = "XT_API_SECRET"


@dataclass(frozen=True)
class PrivateCredentials:
    api_key: str
    api_secret: str


def load_credentials(
    *,
    environ: dict[str, str] | None = None,
) -> PrivateCredentials:
    """Return credentials or raise credentials_missing (fail closed)."""
    env = environ if environ is not None else os.environ
    key = (env.get(ENV_API_KEY) or "").strip()
    secret = (env.get(ENV_API_SECRET) or "").strip()
    if not key or not secret:
        raise XtPrivateError(
            CREDENTIALS_MISSING,
            "XT private credentials are not configured.",
        )
    return PrivateCredentials(api_key=key, api_secret=secret)
