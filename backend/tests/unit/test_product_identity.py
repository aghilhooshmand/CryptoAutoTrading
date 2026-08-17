"""Unit tests for venue-neutral product identity."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.market_data.identity import (
    ProductIdentityError,
    identity_from_row,
    infer_venue,
    kraken_starter_identity,
    resolve_product_identity,
)


def test_xt_form_symbol_infers_xt_venue() -> None:
    ident = resolve_product_identity({"symbol": "btc_usdt"})
    assert ident.venue == "xt"
    assert ident.venue_product_id == "btc_usdt"
    assert ident.canonical_symbol == "BTC/USDT"
    assert ident.symbol_alias == "btc_usdt"


def test_kraken_canonical_round_trip() -> None:
    ident = resolve_product_identity(
        {
            "venue": "kraken",
            "baseAsset": "BTC",
            "quoteAsset": "EUR",
            "canonicalSymbol": "BTC/EUR",
            "venueProductId": "XXBTZEUR",
        }
    )
    assert ident.venue == "kraken"
    assert ident.symbol_alias == "BTC/EUR"
    assert ident.venue_product_id == "XXBTZEUR"


def test_null_venue_row_with_xt_symbol() -> None:
    row = SimpleNamespace(
        venue=None,
        symbol="eth_usdt",
        base_asset=None,
        quote_asset=None,
        canonical_symbol=None,
        venue_product_id=None,
    )
    ident = identity_from_row(row)
    assert ident.venue == "xt"
    assert ident.venue_product_id == "eth_usdt"


def test_infer_venue_defaults_to_kraken() -> None:
    assert infer_venue("BTC/EUR") == "kraken"
    assert infer_venue("btc_usdt") == "xt"


def test_kraken_starter_is_btc_eur() -> None:
    ident = kraken_starter_identity()
    assert ident.canonical_symbol == "BTC/EUR"
    assert ident.venue_product_id == "XXBTZEUR"


def test_missing_identity_rejected() -> None:
    with pytest.raises(ProductIdentityError):
        resolve_product_identity({})
