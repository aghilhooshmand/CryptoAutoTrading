"""Kraken public REST market-data adapter (Feature 002 amendment)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.identity import (
    VENUE_KRAKEN,
    normalize_asset,
    pick_default_kraken_pair,
)
from app.market_data.models import (
    CandleInterval,
    Candlestick,
    CandlestickSeries,
    MarketQuote,
    MarketStatus,
    PairStatus,
    TradingPair,
)

KRAKEN_PUBLIC_BASE = "https://api.kraken.com"
DEFAULT_TIMEOUT = 10.0
KRAKEN_OHLC_INTERVAL: dict[CandleInterval, int] = {
    CandleInterval.M1: 1,
    CandleInterval.M5: 5,
    CandleInterval.M15: 15,
    CandleInterval.H1: 60,
    CandleInterval.H4: 240,
    CandleInterval.D1: 1440,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_decimal_string(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError):
        return None


def _require_result(payload: Any) -> Any:
    if not isinstance(payload, dict):
        raise MarketDataAdapterError("Malformed Kraken response envelope")
    errors = payload.get("error") or []
    if errors:
        raise MarketDataAdapterError(f"Kraken API error: {errors[0]}")
    return payload.get("result")


def map_asset_pair(pair_id: str, row: dict[str, Any]) -> Optional[TradingPair]:
    if not isinstance(row, dict):
        return None
    status = str(row.get("status") or "online").lower()
    if status not in ("", "online"):
        return None
    wsname = str(row.get("wsname") or "").strip()
    base_raw = str(row.get("base") or "")
    quote_raw = str(row.get("quote") or "")
    if wsname and "/" in wsname:
        left, right = wsname.split("/", 1)
        base = normalize_asset(left)
        quote = normalize_asset(right)
    else:
        base = normalize_asset(base_raw)
        quote = normalize_asset(quote_raw)
    if not base or not quote:
        return None
    canonical = f"{base}/{quote}"
    return TradingPair(
        symbol=canonical,
        displayName=canonical,
        baseCurrency=base.lower(),
        quoteCurrency=quote.lower(),
        status=PairStatus.TRADABLE,
        venue=VENUE_KRAKEN,
        venueProductId=pair_id,
        canonicalSymbol=canonical,
        baseAsset=base,
        quoteAsset=quote,
    )


def map_ticker_result(
    pair_id: str,
    row: dict[str, Any],
    *,
    retrieved_at: datetime,
    canonical_symbol: str,
) -> MarketQuote:
    if not isinstance(row, dict):
        raise MarketDataAdapterError("Malformed Kraken ticker")
    last_list = row.get("c")
    last_price = None
    if isinstance(last_list, list) and last_list:
        last_price = _as_decimal_string(last_list[0])
    if last_price is None:
        raise MarketDataAdapterError("Malformed Kraken ticker: missing last price")
    open_price = _as_decimal_string(row.get("o"))
    change_abs = None
    change_pct = None
    if open_price is not None:
        try:
            last_d = Decimal(last_price)
            open_d = Decimal(open_price)
            change_abs = format(last_d - open_d, "f")
            if open_d != 0:
                points = (last_d - open_d) / open_d * Decimal("100")
                text = format(points, "f")
                if "." in text:
                    text = text.rstrip("0").rstrip(".")
                change_pct = text if text else "0"
        except (InvalidOperation, ValueError):
            pass
    high = row.get("h")
    low = row.get("l")
    vol = row.get("v")
    high24 = _as_decimal_string(high[1]) if isinstance(high, list) and len(high) > 1 else None
    low24 = _as_decimal_string(low[1]) if isinstance(low, list) and len(low) > 1 else None
    vol24 = _as_decimal_string(vol[1]) if isinstance(vol, list) and len(vol) > 1 else None
    return MarketQuote(
        symbol=canonical_symbol,
        lastPrice=last_price,
        changeAbsolute=change_abs,
        changePercent=change_pct,
        high24h=high24,
        low24h=low24,
        volumeBase=vol24,
        source=VENUE_KRAKEN,
        observedAt=retrieved_at,
        retrievedAt=retrieved_at,
        status=MarketStatus.FRESH,
    )


def map_ohlc_result(
    rows: list[Any],
    *,
    canonical_symbol: str,
    interval: CandleInterval,
    retrieved_at: datetime,
) -> CandlestickSeries:
    candles: list[Candlestick] = []
    if not isinstance(rows, list):
        raise MarketDataAdapterError("Malformed Kraken OHLC result")
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue
        try:
            open_time = int(row[0]) * 1000
        except (TypeError, ValueError):
            continue
        open_p = _as_decimal_string(row[1])
        high_p = _as_decimal_string(row[2])
        low_p = _as_decimal_string(row[3])
        close_p = _as_decimal_string(row[4])
        vol = _as_decimal_string(row[6])
        if None in (open_p, high_p, low_p, close_p):
            continue
        candles.append(
            Candlestick(
                openTime=open_time,
                open=open_p or "0",
                high=high_p or "0",
                low=low_p or "0",
                close=close_p or "0",
                volumeBase=vol,
            )
        )
    return CandlestickSeries(
        symbol=canonical_symbol,
        interval=interval,
        candles=candles,
        source=VENUE_KRAKEN,
        retrievedAt=retrieved_at,
    )


class KrakenPublicAdapter:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = KRAKEN_PUBLIC_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        pairs_cache_seconds: float = 60.0,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._pairs_cache: list[TradingPair] | None = None
        self._pairs_cache_at: datetime | None = None
        self._pairs_cache_seconds = pairs_cache_seconds

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise MarketDataAdapterError("Kraken request timed out") from exc
        except httpx.HTTPError as exc:
            raise MarketDataAdapterError(f"Kraken HTTP error: {exc}") from exc
        except ValueError as exc:
            raise MarketDataAdapterError("Malformed Kraken JSON response") from exc

    async def list_spot_pairs(self) -> list[TradingPair]:
        now = _utc_now()
        if (
            self._pairs_cache is not None
            and self._pairs_cache_at is not None
            and (now - self._pairs_cache_at).total_seconds() < self._pairs_cache_seconds
        ):
            return list(self._pairs_cache)
        payload = await self._get_json("/0/public/AssetPairs")
        result = _require_result(payload)
        if not isinstance(result, dict):
            raise MarketDataAdapterError("Malformed Kraken AssetPairs result")
        pairs: list[TradingPair] = []
        for pair_id, row in result.items():
            mapped = map_asset_pair(str(pair_id), row) if isinstance(row, dict) else None
            if mapped is not None:
                pairs.append(mapped)
        pairs.sort(key=lambda p: p.canonicalSymbol or p.symbol)
        self._pairs_cache = pairs
        self._pairs_cache_at = now
        return list(pairs)

    async def _resolve_pair(self, symbol: str) -> TradingPair:
        needle = symbol.strip()
        pairs = await self.list_spot_pairs()
        for pair in pairs:
            ids = {
                pair.symbol,
                pair.displayName,
                pair.canonicalSymbol,
                pair.venueProductId,
                (pair.canonicalSymbol or "").replace("/", ""),
            }
            if needle in ids or needle.upper() in {str(x).upper() for x in ids if x}:
                return pair
        raise UnsupportedSymbolError(symbol)

    async def get_quote(self, symbol: str) -> MarketQuote:
        pair = await self._resolve_pair(symbol)
        payload = await self._get_json(
            "/0/public/Ticker", params={"pair": pair.venueProductId}
        )
        result = _require_result(payload)
        if not isinstance(result, dict) or not result:
            raise MarketDataAdapterError("Malformed Kraken ticker result")
        _pair_id, row = next(iter(result.items()))
        return map_ticker_result(
            pair.venueProductId or "",
            row,
            retrieved_at=_utc_now(),
            canonical_symbol=pair.canonicalSymbol or pair.symbol,
        )

    async def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        pair = await self._resolve_pair(symbol)
        kraken_interval = KRAKEN_OHLC_INTERVAL.get(interval)
        if kraken_interval is None:
            raise MarketDataAdapterError(f"Unsupported candle interval for Kraken: {interval}")
        params: dict[str, Any] = {
            "pair": pair.venueProductId,
            "interval": kraken_interval,
        }
        if start_time is not None:
            params["since"] = int(start_time / 1000)
        payload = await self._get_json("/0/public/OHLC", params=params)
        result = _require_result(payload)
        if not isinstance(result, dict):
            raise MarketDataAdapterError("Malformed Kraken OHLC result")
        rows = None
        for key, value in result.items():
            if key == "last":
                continue
            rows = value
            break
        series = map_ohlc_result(
            rows if isinstance(rows, list) else [],
            canonical_symbol=pair.canonicalSymbol or pair.symbol,
            interval=interval,
            retrieved_at=_utc_now(),
        )
        candles = series.candles
        if end_time is not None:
            candles = [c for c in candles if c.openTime <= end_time]
        if start_time is not None:
            candles = [c for c in candles if c.openTime >= start_time]
        if limit and len(candles) > limit:
            candles = candles[-limit:]
        return series.model_copy(update={"candles": candles})


def default_kraken_symbol(pairs: list[TradingPair]) -> str | None:
    picked = pick_default_kraken_pair(pairs)
    if picked is None:
        return None
    return picked.canonicalSymbol or picked.symbol
