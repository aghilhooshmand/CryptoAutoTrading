"""Venue-neutral product identity (Feature 002 amendment 2026-08-17)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

VENUE_KRAKEN = "kraken"
VENUE_XT = "xt"
DEFAULT_VENUE = VENUE_KRAKEN

# Product-starter preference only — not a constitutional quote lock.
KRAKEN_STARTER_BASE = "BTC"
KRAKEN_STARTER_QUOTE = "EUR"
KRAKEN_STARTER_CANONICAL = "BTC/EUR"
KRAKEN_STARTER_PRODUCT_ID = "XXBTZEUR"

_KRAKEN_ASSET_ALIASES = {
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZJPY": "JPY",
    "ZCAD": "CAD",
    "ZAUD": "AUD",
}

_KRAKEN_PRODUCT_HINTS = {
    ("BTC", "EUR"): "XXBTZEUR",
    ("BTC", "USD"): "XXBTZUSD",
    ("BTC", "USDT"): "XBTUSDT",
}


class ProductIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class ProductIdentity:
    venue: str
    base_asset: str
    quote_asset: str
    canonical_symbol: str
    venue_product_id: str

    @property
    def symbol_alias(self) -> str:
        """Compatibility `symbol`: XT wire id, otherwise canonical."""
        if self.venue == VENUE_XT:
            return self.venue_product_id
        return self.canonical_symbol

    def to_api(self) -> dict[str, str]:
        return {
            "venue": self.venue,
            "baseAsset": self.base_asset,
            "quoteAsset": self.quote_asset,
            "canonicalSymbol": self.canonical_symbol,
            "venueProductId": self.venue_product_id,
            "symbol": self.symbol_alias,
        }


def normalize_asset(code: str) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        return ""
    if raw in _KRAKEN_ASSET_ALIASES:
        return _KRAKEN_ASSET_ALIASES[raw]
    if raw.startswith("Z") and len(raw) == 4 and raw[1:].isalpha():
        return raw[1:]
    if raw.startswith("X") and len(raw) == 4:
        rest = raw[1:]
        return _KRAKEN_ASSET_ALIASES.get(rest, rest)
    return raw


def is_xt_form_symbol(raw: str) -> bool:
    text = (raw or "").strip().lower()
    if not text or "/" in text or "-" in text:
        return False
    parts = text.split("_")
    return len(parts) == 2 and all(parts)


def normalize_venue(raw: str | None) -> str:
    if raw is None or str(raw).strip() == "":
        return DEFAULT_VENUE
    venue = str(raw).strip().lower()
    if venue not in (VENUE_KRAKEN, VENUE_XT):
        raise ProductIdentityError(f"Unsupported venue: {raw}")
    return venue


def infer_venue(symbol: str | None, explicit_venue: str | None = None) -> str:
    if explicit_venue is not None and str(explicit_venue).strip() != "":
        return normalize_venue(str(explicit_venue))
    if symbol and is_xt_form_symbol(symbol):
        return VENUE_XT
    return DEFAULT_VENUE


def kraken_product_hint(base: str, quote: str) -> str:
    return _KRAKEN_PRODUCT_HINTS.get((base, quote), f"{base}{quote}")


def identity_from_xt_symbol(symbol: str) -> ProductIdentity:
    xt_id = symbol.strip().lower()
    if not is_xt_form_symbol(xt_id):
        raise ProductIdentityError(f"Not an XT-form symbol: {symbol}")
    base_raw, quote_raw = xt_id.split("_", 1)
    base = normalize_asset(base_raw)
    quote = normalize_asset(quote_raw)
    return ProductIdentity(
        venue=VENUE_XT,
        base_asset=base,
        quote_asset=quote,
        canonical_symbol=f"{base}/{quote}",
        venue_product_id=xt_id,
    )


def identity_from_row(row: Any) -> ProductIdentity:
    """Read persisted identity; infer XT from legacy NULL venue + underscore symbol."""
    return resolve_product_identity(
        {
            "venue": getattr(row, "venue", None),
            "symbol": getattr(row, "symbol", None),
            "baseAsset": getattr(row, "base_asset", None),
            "quoteAsset": getattr(row, "quote_asset", None),
            "canonicalSymbol": getattr(row, "canonical_symbol", None),
            "venueProductId": getattr(row, "venue_product_id", None),
        },
        default_venue=None,
    )


def resolve_product_identity(
    data: Mapping[str, Any],
    *,
    default_venue: str | None = None,
) -> ProductIdentity:
    """Resolve identity from create/read payloads or ORM-shaped dicts."""
    venue_raw = data.get("venue")
    symbol = str(data.get("symbol") or "").strip()
    canonical = str(
        data.get("canonicalSymbol") or data.get("canonical_symbol") or ""
    ).strip()
    product_id = str(
        data.get("venueProductId") or data.get("venue_product_id") or ""
    ).strip()
    base = str(data.get("baseAsset") or data.get("base_asset") or "").strip()
    quote = str(data.get("quoteAsset") or data.get("quote_asset") or "").strip()

    probe = product_id or symbol or canonical
    if not probe:
        raise ProductIdentityError("symbol or product identity is required")

    if venue_raw is not None and str(venue_raw).strip() != "":
        venue = normalize_venue(str(venue_raw))
    elif is_xt_form_symbol(probe):
        venue = VENUE_XT
    elif default_venue is not None:
        venue = normalize_venue(default_venue)
    else:
        venue = infer_venue(probe, None)

    if venue == VENUE_XT:
        xt_id = (product_id or symbol).strip().lower()
        if not is_xt_form_symbol(xt_id):
            raise ProductIdentityError("XT identity requires an underscore venue product id")
        parsed = identity_from_xt_symbol(xt_id)
        return ProductIdentity(
            venue=VENUE_XT,
            base_asset=normalize_asset(base) or parsed.base_asset,
            quote_asset=normalize_asset(quote) or parsed.quote_asset,
            canonical_symbol=canonical.upper().replace(" ", "") or parsed.canonical_symbol,
            venue_product_id=xt_id,
        )

    if not canonical and "/" in symbol:
        canonical = symbol
    if not canonical and base and quote:
        canonical = f"{normalize_asset(base)}/{normalize_asset(quote)}"
    if not canonical and "/" in product_id:
        canonical = product_id
    if not canonical:
        raise ProductIdentityError("Kraken identity requires canonicalSymbol or base/quote")

    if "/" in canonical:
        left, right = canonical.split("/", 1)
        base = normalize_asset(base or left)
        quote = normalize_asset(quote or right)
    else:
        base = normalize_asset(base)
        quote = normalize_asset(quote)
        if not base or not quote:
            raise ProductIdentityError("Kraken identity requires baseAsset and quoteAsset")
    canonical = f"{base}/{quote}"
    if not product_id or "/" in product_id:
        product_id = kraken_product_hint(base, quote)
    return ProductIdentity(
        venue=VENUE_KRAKEN,
        base_asset=base,
        quote_asset=quote,
        canonical_symbol=canonical,
        venue_product_id=product_id,
    )


def kraken_starter_identity() -> ProductIdentity:
    return ProductIdentity(
        venue=VENUE_KRAKEN,
        base_asset=KRAKEN_STARTER_BASE,
        quote_asset=KRAKEN_STARTER_QUOTE,
        canonical_symbol=KRAKEN_STARTER_CANONICAL,
        venue_product_id=KRAKEN_STARTER_PRODUCT_ID,
    )


def pick_default_kraken_pair(pairs: list[Any]) -> Any | None:
    if not pairs:
        return None
    preferred = (("BTC", "EUR"), ("BTC", "USD"), ("BTC", "USDT"))
    indexed: dict[tuple[str, str], Any] = {}
    for pair in pairs:
        base = normalize_asset(getattr(pair, "baseAsset", None) or getattr(pair, "baseCurrency", ""))
        quote = normalize_asset(
            getattr(pair, "quoteAsset", None) or getattr(pair, "quoteCurrency", "")
        )
        indexed[(base, quote)] = pair
    for key in preferred:
        if key in indexed:
            return indexed[key]
    for pair in pairs:
        base = normalize_asset(getattr(pair, "baseAsset", None) or getattr(pair, "baseCurrency", ""))
        if base == "BTC":
            return pair
    return pairs[0]


def persistence_columns(ident: ProductIdentity) -> dict[str, str]:
    return {
        "symbol": ident.symbol_alias,
        "venue": ident.venue,
        "base_asset": ident.base_asset,
        "quote_asset": ident.quote_asset,
        "canonical_symbol": ident.canonical_symbol,
        "venue_product_id": ident.venue_product_id,
    }


def identity_api_from_row(row: Any) -> dict[str, str]:
    try:
        return identity_from_row(row).to_api()
    except ProductIdentityError:
        return {"symbol": str(getattr(row, "symbol", "") or "")}


def fetch_key(ident: ProductIdentity) -> str:
    """Wire id used for adapter quote/candle calls."""
    return ident.venue_product_id
