"""Market-data service orchestration over a venue adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.market_data.adapters.base import (
    MarketDataAdapter,
    MarketDataAdapterError,
    UnsupportedSymbolError,
)
from app.market_data.adapters.kraken_public import KrakenPublicAdapter, default_kraken_symbol
from app.market_data.adapters.xt_spot import XtSpotAdapter
from app.market_data.identity import (
    DEFAULT_VENUE,
    VENUE_KRAKEN,
    VENUE_XT,
    ProductIdentity,
    infer_venue,
    is_xt_form_symbol,
    normalize_venue,
)
from app.market_data.models import (
    ALLOWED_INTERVALS,
    CandleInterval,
    CandlestickSeries,
    MarketQuote,
    PairsResponse,
    TradingPair,
)

DEFAULT_CANDLE_LIMIT = 120


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _source_label(venue: str) -> str:
    if venue == VENUE_XT:
        return "XT"
    return venue


def adapter_for(venue: str) -> MarketDataAdapter:
    venue = normalize_venue(venue)
    if venue == VENUE_XT:
        return XtSpotAdapter()
    return KrakenPublicAdapter()


class MarketDataService:
    def __init__(
        self,
        adapter: Optional[MarketDataAdapter] = None,
        *,
        venue: str | None = None,
    ) -> None:
        self._venue = normalize_venue(venue) if venue else DEFAULT_VENUE
        self._adapter: MarketDataAdapter = adapter or adapter_for(self._venue)

    @property
    def venue(self) -> str:
        return self._venue

    async def _list_pairs(self) -> list[TradingPair]:
        list_spot = getattr(self._adapter, "list_spot_pairs", None)
        if list_spot is not None:
            return await list_spot()
        return await self._adapter.list_usdt_pairs()  # type: ignore[attr-defined]

    async def list_pairs(self) -> PairsResponse:
        pairs = await self._list_pairs()
        return PairsResponse(
            source=_source_label(self._venue),
            retrievedAt=_utc_now(),
            pairs=pairs,
        )

    def pick_default_symbol(self, pairs: list[TradingPair]) -> Optional[str]:
        if not pairs:
            return None
        if self._venue == VENUE_KRAKEN:
            return default_kraken_symbol(pairs)
        for preferred in ("btc_usdt",):
            if any(p.symbol == preferred for p in pairs):
                return preferred
        return pairs[0].symbol

    def _guard_cross_venue(self, symbol: str) -> None:
        if self._venue == VENUE_KRAKEN and is_xt_form_symbol(symbol):
            raise UnsupportedSymbolError(symbol)
        if self._venue == VENUE_XT and not is_xt_form_symbol(symbol) and "/" in symbol:
            raise UnsupportedSymbolError(symbol)

    async def get_quote(self, symbol: str) -> MarketQuote:
        self._guard_cross_venue(symbol)
        return await self._adapter.get_quote(symbol)

    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = DEFAULT_CANDLE_LIMIT,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        if interval not in ALLOWED_INTERVALS:
            raise ValueError(f"Invalid interval: {interval}")
        self._guard_cross_venue(symbol)
        return await self._adapter.get_candles(
            symbol,
            CandleInterval(interval),
            limit,
            start_time=start_time,
            end_time=end_time,
        )


_default_service: Optional[MarketDataService] = None
_venue_services: dict[str, MarketDataService] = {}


def get_market_data_service() -> MarketDataService:
    global _default_service
    if _default_service is not None:
        return _default_service
    if DEFAULT_VENUE not in _venue_services:
        _venue_services[DEFAULT_VENUE] = MarketDataService(venue=DEFAULT_VENUE)
    return _venue_services[DEFAULT_VENUE]


def market_data_service_for(venue: str | None, *, symbol: str | None = None) -> MarketDataService:
    if _default_service is not None:
        return _default_service
    resolved = infer_venue(symbol, venue)
    if resolved not in _venue_services:
        _venue_services[resolved] = MarketDataService(venue=resolved)
    return _venue_services[resolved]


def set_market_data_service(service: Optional[MarketDataService]) -> None:
    global _default_service
    _default_service = service
    if service is None:
        _venue_services.clear()


def bound_market_data_service(
    venue: str | None,
    symbol: str | None,
    *,
    injected: Optional[MarketDataService] = None,
) -> MarketDataService:
    """Prefer test doubles; otherwise return the venue-matching live service."""
    if injected is not None and not isinstance(injected, MarketDataService):
        return injected  # type: ignore[return-value]
    if _default_service is not None:
        return _default_service
    return market_data_service_for(venue, symbol=symbol)


def bound_service_for_identity(
    ident: ProductIdentity,
    *,
    injected: Optional[MarketDataService] = None,
) -> tuple[MarketDataService, str]:
    key = ident.venue_product_id
    return bound_market_data_service(ident.venue, key, injected=injected), key


__all__ = [
    "MarketDataService",
    "get_market_data_service",
    "market_data_service_for",
    "set_market_data_service",
    "bound_market_data_service",
    "bound_service_for_identity",
    "adapter_for",
    "MarketDataAdapterError",
    "UnsupportedSymbolError",
    "DEFAULT_CANDLE_LIMIT",
]
