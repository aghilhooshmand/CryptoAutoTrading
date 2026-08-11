"""Market data adapter protocol."""

from __future__ import annotations

from typing import Protocol

from app.market_data.models import CandleInterval, CandlestickSeries, MarketQuote, TradingPair


class MarketDataAdapterError(Exception):
    """Raised when exchange market data cannot be retrieved or normalized."""

    def __init__(self, message: str, *, code: str = "market_data_unavailable") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class UnsupportedSymbolError(MarketDataAdapterError):
    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Symbol is not a supported USDT Spot pair: {symbol}",
            code="unsupported",
        )
        self.symbol = symbol


class MarketDataAdapter(Protocol):
    async def list_usdt_pairs(self) -> list[TradingPair]:
        """Return supported XT Spot pairs quoted in USDT."""

    async def get_quote(self, symbol: str) -> MarketQuote:
        """Return normalized quote for a supported symbol."""

    async def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        """Return normalized candlesticks; optional UTC-ms start/end for range fetch."""
