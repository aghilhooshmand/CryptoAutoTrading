"""Market-data service orchestration over an exchange adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.market_data.adapters.base import (
    MarketDataAdapter,
    MarketDataAdapterError,
    UnsupportedSymbolError,
)
from app.market_data.adapters.xt_spot import XtSpotAdapter
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


class MarketDataService:
    def __init__(self, adapter: Optional[MarketDataAdapter] = None) -> None:
        self._adapter: MarketDataAdapter = adapter or XtSpotAdapter()

    async def list_pairs(self) -> PairsResponse:
        pairs = await self._adapter.list_usdt_pairs()
        return PairsResponse(source="XT", retrievedAt=_utc_now(), pairs=pairs)

    def pick_default_symbol(self, pairs: list[TradingPair]) -> Optional[str]:
        if not pairs:
            return None
        for preferred in ("btc_usdt",):
            if any(p.symbol == preferred for p in pairs):
                return preferred
        return pairs[0].symbol

    async def get_quote(self, symbol: str) -> MarketQuote:
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
        return await self._adapter.get_candles(
            symbol,
            CandleInterval(interval),
            limit,
            start_time=start_time,
            end_time=end_time,
        )


# Shared default service for FastAPI routes (overridable in tests).
_default_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    global _default_service
    if _default_service is None:
        _default_service = MarketDataService()
    return _default_service


def set_market_data_service(service: Optional[MarketDataService]) -> None:
    global _default_service
    _default_service = service


__all__ = [
    "MarketDataService",
    "get_market_data_service",
    "set_market_data_service",
    "MarketDataAdapterError",
    "UnsupportedSymbolError",
    "DEFAULT_CANDLE_LIMIT",
]
