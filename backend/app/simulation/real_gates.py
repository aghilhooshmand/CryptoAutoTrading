"""Real-mode create/confirm gates (Feature 015) — sync helpers for XT free."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from app.xt_account.credentials import load_credentials
from app.xt_account.errors import CREDENTIALS_MISSING, XtPrivateError
from app.xt_account.normalize import normalize_balances

REAL_ALLOCATED_CAP = Decimal("50")

# Tests may replace this to avoid live XT.
TryFreeUsdtFn = Callable[[], Decimal | None]
_try_free_usdt_override: TryFreeUsdtFn | None = None


def set_try_free_usdt_override(fn: TryFreeUsdtFn | None) -> None:
    global _try_free_usdt_override
    _try_free_usdt_override = fn


def require_real_credentials() -> None:
    load_credentials()


def try_xt_free_usdt() -> Decimal | None:
    """Return free USDT if balances readable; None if fetch failed (non-credentials)."""
    if _try_free_usdt_override is not None:
        return _try_free_usdt_override()
    try:
        creds = load_credentials()
    except XtPrivateError as exc:
        if exc.code == CREDENTIALS_MISSING:
            raise
        return None

    import asyncio

    from app.xt_account.client import XtPrivateClient

    async def _fetch() -> Decimal | None:
        client = XtPrivateClient(creds)
        try:
            raw = await client.get_balances()
            balances = normalize_balances(raw)
            for bal in balances:
                if bal.asset.lower() == "usdt":
                    return Decimal(bal.free)
            return Decimal("0")
        except XtPrivateError:
            return None
        finally:
            await client.aclose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_fetch())
    # Already in async context — cannot asyncio.run; leave unread.
    _ = loop
    return None
