"""Unit tests for Feature 009 public-quote valuation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market_data.models import MarketQuote, MarketStatus
from app.portfolio.valuation import QuoteView, classify_market_quote, is_supported_non_quote_asset, usdt_quote


def _quote(*, last: str, status: MarketStatus, age_seconds: int) -> MarketQuote:
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    observed = now - timedelta(seconds=age_seconds)
    return MarketQuote(
        symbol="btc_usdt",
        lastPrice=last,
        observedAt=observed,
        retrievedAt=now,
        status=status,
        source="XT",
    )


def test_usdt_is_one_to_one_fresh():
    q = usdt_quote()
    assert q.price == Decimal("1")
    assert q.status == "fresh"


def test_fresh_quote_within_sixty_seconds():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    view = classify_market_quote(_quote(last="90000", status=MarketStatus.FRESH, age_seconds=10), now)
    assert view == QuoteView(price=Decimal("90000"), status="fresh")


def test_stale_last_known_is_included():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    view = classify_market_quote(_quote(last="90000", status=MarketStatus.FRESH, age_seconds=120), now)
    assert view.price == Decimal("90000")
    assert view.status == "stale"


def test_explicit_stale_status_included():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    view = classify_market_quote(_quote(last="80000", status=MarketStatus.STALE, age_seconds=5), now)
    assert view.price == Decimal("80000")
    assert view.status == "stale"


def test_unavailable_does_not_invent_price():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    view = classify_market_quote(
        _quote(last="90000", status=MarketStatus.UNAVAILABLE, age_seconds=0),
        now,
    )
    assert view.price is None
    assert view.status == "unavailable"


def test_invalid_last_price_unavailable():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    view = classify_market_quote(_quote(last="not-a-price", status=MarketStatus.FRESH, age_seconds=0), now)
    assert view.price is None
    assert view.status == "unavailable"


def test_supported_non_quote_assets():
    assert is_supported_non_quote_asset("btc")
    assert is_supported_non_quote_asset("ETH")
    assert not is_supported_non_quote_asset("usdt")
    assert not is_supported_non_quote_asset("notacoin")
