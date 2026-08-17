"""Internal market-data models (normalized; no XT payload shapes)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class PairStatus(str, Enum):
    TRADABLE = "tradable"
    UNAVAILABLE = "unavailable"


class MarketStatus(str, Enum):
    LOADING = "loading"
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class CandleInterval(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


ALLOWED_INTERVALS = frozenset(i.value for i in CandleInterval)


class TradingPair(BaseModel):
    symbol: str
    displayName: str
    baseCurrency: str
    quoteCurrency: str
    status: PairStatus = PairStatus.TRADABLE
    venue: str = "xt"
    venueProductId: Optional[str] = None
    canonicalSymbol: Optional[str] = None
    baseAsset: Optional[str] = None
    quoteAsset: Optional[str] = None

    @model_validator(mode="after")
    def _fill_identity(self) -> "TradingPair":
        if not self.venueProductId:
            self.venueProductId = self.symbol
        if not self.canonicalSymbol:
            self.canonicalSymbol = self.displayName.replace("_", "/")
        if not self.baseAsset:
            self.baseAsset = (self.baseCurrency or "").upper()
        if not self.quoteAsset:
            self.quoteAsset = (self.quoteCurrency or "").upper()
        return self


class MarketQuote(BaseModel):
    symbol: str
    lastPrice: str
    changeAbsolute: Optional[str] = None
    changePercent: Optional[str] = None
    high24h: Optional[str] = None
    low24h: Optional[str] = None
    volumeBase: Optional[str] = None
    volumeQuote: Optional[str] = None
    source: str = ""
    observedAt: datetime
    retrievedAt: datetime
    status: MarketStatus = MarketStatus.FRESH


class Candlestick(BaseModel):
    openTime: int
    open: str
    high: str
    low: str
    close: str
    volumeBase: Optional[str] = None
    volumeQuote: Optional[str] = None


class CandlestickSeries(BaseModel):
    symbol: str
    interval: CandleInterval
    candles: list[Candlestick] = Field(default_factory=list)
    source: str = ""
    retrievedAt: datetime


class PairsResponse(BaseModel):
    source: str = ""
    retrievedAt: datetime
    pairs: list[TradingPair]


class MarketDataErrorBody(BaseModel):
    code: str
    message: str


class MarketDataErrorResponse(BaseModel):
    error: MarketDataErrorBody
