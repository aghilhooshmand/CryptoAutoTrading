"""Public-quote valuation for portfolio holdings (Feature 009)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.adapters.base import UnsupportedSymbolError
from app.market_data.models import MarketQuote, MarketStatus
from app.market_data.service import get_market_data_service
from app.portfolio import identity

QUOTE_ASSET = identity.QUOTE_ASSET
QUOTE_PRICE = Decimal("1")
STALE_AFTER_SECONDS = 60

# Feature 002 USDT-quoted bases commonly held after simulated fills.
SUPPORTED_NON_QUOTE_ASSETS = frozenset(
    {
        "btc",
        "eth",
        "sol",
        "xrp",
        "ada",
        "doge",
        "bnb",
        "ltc",
        "link",
        "avax",
        "dot",
        "matic",
        "atom",
        "uni",
        "near",
    }
)


@dataclass(frozen=True)
class QuoteView:
    price: Decimal | None
    status: str  # fresh | stale | unavailable


def is_supported_non_quote_asset(asset: str) -> bool:
    return asset.lower().strip() in SUPPORTED_NON_QUOTE_ASSETS


def usdt_quote() -> QuoteView:
    return QuoteView(price=QUOTE_PRICE, status="fresh")


def classify_market_quote(quote: MarketQuote, now: datetime | None = None) -> QuoteView:
    """Map a Feature 002 public quote into a holding price view. Never invent a price."""
    now = now or datetime.now(timezone.utc)
    if quote.status in (
        MarketStatus.UNAVAILABLE,
        MarketStatus.UNSUPPORTED,
        MarketStatus.ERROR,
        MarketStatus.LOADING,
    ):
        return QuoteView(price=None, status="unavailable")
    try:
        price = identity.parse_money(quote.lastPrice)
    except identity.CapitalIdentityError:
        return QuoteView(price=None, status="unavailable")
    if price <= 0:
        return QuoteView(price=None, status="unavailable")

    ts = quote.observedAt or quote.retrievedAt
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (now - ts).total_seconds()
    stale = quote.status == MarketStatus.STALE or age > STALE_AFTER_SECONDS
    return QuoteView(price=price, status="stale" if stale else "fresh")


async def fetch_quotes(
    assets: list[str],
    *,
    now: datetime | None = None,
    service=None,
) -> dict[str, QuoteView]:
    """Fetch public `{asset}_usdt` quotes. Failures become unavailable, not invented prices."""
    now = now or datetime.now(timezone.utc)
    md = service or get_market_data_service()
    out: dict[str, QuoteView] = {}
    for raw in assets:
        asset = raw.lower().strip()
        if asset == QUOTE_ASSET:
            out[asset] = usdt_quote()
            continue
        try:
            quote = await md.get_quote(f"{asset}_usdt")
            out[asset] = classify_market_quote(quote, now)
        except UnsupportedSymbolError:
            out[asset] = QuoteView(price=None, status="unavailable")
        except Exception:
            out[asset] = QuoteView(price=None, status="unavailable")
    return out
