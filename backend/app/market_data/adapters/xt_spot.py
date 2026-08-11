"""XT.COM public Spot REST market-data adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.models import (
    CandleInterval,
    Candlestick,
    CandlestickSeries,
    MarketQuote,
    MarketStatus,
    PairStatus,
    TradingPair,
)

XT_SPOT_BASE = "https://sapi.xt.com"
DEFAULT_TIMEOUT = 10.0

# XT Spot kline `interval` query values — keep exchange-specific strings here only.
XT_KLINE_INTERVAL: dict[CandleInterval, str] = {
    CandleInterval.M1: "1m",
    CandleInterval.M5: "5m",
    CandleInterval.M15: "15m",
    CandleInterval.H1: "1h",
    CandleInterval.H4: "4h",
    CandleInterval.D1: "1d",
}


def to_xt_kline_interval(interval: CandleInterval) -> str:
    try:
        return XT_KLINE_INTERVAL[interval]
    except KeyError as exc:
        raise MarketDataAdapterError(f"Unsupported candle interval for XT: {interval}") from exc


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ms_to_datetime(ms: int | float | str) -> datetime:
    return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc)


def _as_decimal_string(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError):
        return None


def ratio_to_percent_points(ratio: Any) -> Optional[str]:
    """Convert XT change ratio (e.g. 0.0235) to percent points (\"2.35\")."""
    if ratio is None or ratio == "":
        return None
    try:
        points = Decimal(str(ratio)) * Decimal("100")
        text = format(points, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text if text else "0"
    except (InvalidOperation, ValueError):
        return None


def _require_envelope(payload: Any) -> Any:
    if not isinstance(payload, dict):
        raise MarketDataAdapterError("Malformed XT response envelope")
    if payload.get("rc") != 0 or payload.get("mc") != "SUCCESS":
        raise MarketDataAdapterError(
            f"XT API error: rc={payload.get('rc')} mc={payload.get('mc')}"
        )
    return payload.get("result")


def map_symbol_row(row: dict[str, Any]) -> Optional[TradingPair]:
    if not isinstance(row, dict):
        return None
    quote = str(row.get("quoteCurrency") or "").lower()
    if quote != "usdt":
        return None
    state = str(row.get("state") or "").upper()
    trading_enabled = bool(row.get("tradingEnabled", False))
    openapi_enabled = bool(row.get("openapiEnabled", False))
    if state != "ONLINE" or not trading_enabled or not openapi_enabled:
        return None
    symbol = str(row.get("symbol") or "").lower()
    if not symbol:
        return None
    display = str(row.get("displayName") or symbol.replace("_", "/").upper())
    base = str(row.get("baseCurrency") or symbol.split("_")[0]).lower()
    return TradingPair(
        symbol=symbol,
        displayName=display,
        baseCurrency=base,
        quoteCurrency="usdt",
        status=PairStatus.TRADABLE,
    )


def map_ticker_row(row: dict[str, Any], *, retrieved_at: datetime) -> MarketQuote:
    symbol = str(row.get("s") or "").lower()
    last_price = _as_decimal_string(row.get("c"))
    if not symbol or last_price is None:
        raise MarketDataAdapterError("Malformed XT ticker: missing symbol or last price")

    observed_raw = row.get("t")
    observed_at = (
        _ms_to_datetime(observed_raw) if observed_raw is not None else retrieved_at
    )

    return MarketQuote(
        symbol=symbol,
        lastPrice=last_price,
        changeAbsolute=_as_decimal_string(row.get("cv")),
        changePercent=ratio_to_percent_points(row.get("cr")),
        high24h=_as_decimal_string(row.get("h")),
        low24h=_as_decimal_string(row.get("l")),
        volumeBase=_as_decimal_string(row.get("q")),
        volumeQuote=_as_decimal_string(row.get("v")),
        source="XT",
        observedAt=observed_at,
        retrievedAt=retrieved_at,
        status=MarketStatus.FRESH,
    )


def map_kline_rows(
    rows: list[Any],
    *,
    symbol: str,
    interval: CandleInterval,
    retrieved_at: datetime,
) -> CandlestickSeries:
    candles: list[Candlestick] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        open_time = row.get("t")
        o = _as_decimal_string(row.get("o"))
        h = _as_decimal_string(row.get("h"))
        low = _as_decimal_string(row.get("l"))
        c = _as_decimal_string(row.get("c"))
        if open_time is None or o is None or h is None or low is None or c is None:
            continue
        candles.append(
            Candlestick(
                openTime=int(open_time),
                open=o,
                high=h,
                low=low,
                close=c,
                volumeBase=_as_decimal_string(row.get("q")),
                volumeQuote=_as_decimal_string(row.get("v")),
            )
        )
    candles.sort(key=lambda bar: bar.openTime)
    return CandlestickSeries(
        symbol=symbol,
        interval=interval,
        candles=candles,
        source="XT",
        retrievedAt=retrieved_at,
    )


class XtSpotAdapter:
    """Public Spot REST client for XT.COM (`sapi.xt.com`)."""

    def __init__(
        self,
        *,
        base_url: str = XT_SPOT_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.AsyncClient] = None,
        pairs_cache_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None
        self._pairs_cache_seconds = pairs_cache_seconds
        self._pairs_cache: Optional[list[TradingPair]] = None
        self._pairs_cache_at: Optional[datetime] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"User-Agent": "CryptoAutoTrading/0.2"},
            )
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_json(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        client = await self._get_client()
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise MarketDataAdapterError("XT request timed out") from exc
        except httpx.HTTPError as exc:
            raise MarketDataAdapterError(f"XT HTTP error: {exc}") from exc
        except ValueError as exc:
            raise MarketDataAdapterError("Malformed XT JSON response") from exc

    async def list_usdt_pairs(self) -> list[TradingPair]:
        now = _utc_now()
        if (
            self._pairs_cache is not None
            and self._pairs_cache_at is not None
            and (now - self._pairs_cache_at).total_seconds() < self._pairs_cache_seconds
        ):
            return list(self._pairs_cache)

        payload = await self._get_json("/v4/public/symbol")
        result = _require_envelope(payload)
        if not isinstance(result, dict):
            raise MarketDataAdapterError("Malformed XT symbol result")
        symbols = result.get("symbols")
        if not isinstance(symbols, list):
            raise MarketDataAdapterError("Malformed XT symbols list")
        pairs: list[TradingPair] = []
        for row in symbols:
            mapped = map_symbol_row(row) if isinstance(row, dict) else None
            if mapped is not None:
                pairs.append(mapped)
        pairs.sort(key=lambda p: p.symbol)
        self._pairs_cache = pairs
        self._pairs_cache_at = now
        return list(pairs)

    async def _ensure_supported(self, symbol: str) -> str:
        normalized = symbol.strip().lower()
        pairs = await self.list_usdt_pairs()
        if not any(p.symbol == normalized for p in pairs):
            raise UnsupportedSymbolError(normalized)
        return normalized

    async def get_quote(self, symbol: str) -> MarketQuote:
        normalized = await self._ensure_supported(symbol)
        retrieved_at = _utc_now()
        payload = await self._get_json(
            "/v4/public/ticker", params={"symbol": normalized}
        )
        result = _require_envelope(payload)
        if not isinstance(result, list) or not result:
            raise MarketDataAdapterError("Malformed XT ticker result")
        row = result[0]
        if not isinstance(row, dict):
            raise MarketDataAdapterError("Malformed XT ticker row")
        quote = map_ticker_row(row, retrieved_at=retrieved_at)
        if quote.symbol != normalized:
            raise MarketDataAdapterError("XT ticker symbol mismatch")
        return quote

    async def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> CandlestickSeries:
        normalized = await self._ensure_supported(symbol)
        retrieved_at = _utc_now()
        xt_interval = to_xt_kline_interval(interval)

        if start_time is None and end_time is None:
            safe_limit = max(1, min(int(limit), 1000))
            payload = await self._get_json(
                "/v4/public/kline",
                params={
                    "symbol": normalized,
                    "interval": xt_interval,
                    "limit": safe_limit,
                },
            )
            result = _require_envelope(payload)
            if not isinstance(result, list):
                raise MarketDataAdapterError("Malformed XT kline result")
            return map_kline_rows(
                result,
                symbol=normalized,
                interval=interval,
                retrieved_at=retrieved_at,
            )

        # Ranged / paginated fetch (Feature 004). XT page size max 1000.
        step_map = {
            CandleInterval.M1: 60_000,
            CandleInterval.M5: 5 * 60_000,
            CandleInterval.M15: 15 * 60_000,
            CandleInterval.H1: 60 * 60_000,
            CandleInterval.H4: 4 * 60 * 60_000,
            CandleInterval.D1: 24 * 60 * 60_000,
        }
        step = step_map[interval]
        cursor = int(start_time) if start_time is not None else 0
        end_bound = int(end_time) if end_time is not None else cursor + step * 1000
        merged: list[dict] = []
        seen: set[int] = set()
        while cursor < end_bound and len(merged) < 5000:
            payload = await self._get_json(
                "/v4/public/kline",
                params={
                    "symbol": normalized,
                    "interval": xt_interval,
                    "limit": 1000,
                    "startTime": cursor,
                    "endTime": end_bound,
                },
            )
            result = _require_envelope(payload)
            if not isinstance(result, list) or not result:
                break
            batch_times: list[int] = []
            for row in result:
                if not isinstance(row, dict):
                    continue
                t = row.get("t")
                if t is None:
                    continue
                ot = int(t)
                if start_time is not None and ot < int(start_time):
                    continue
                if end_time is not None and ot >= int(end_time):
                    continue
                if ot in seen:
                    continue
                seen.add(ot)
                merged.append(row)
                batch_times.append(ot)
            if not batch_times:
                break
            next_cursor = max(batch_times) + step
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(result) < 1000:
                break

        return map_kline_rows(
            merged,
            symbol=normalized,
            interval=interval,
            retrieved_at=retrieved_at,
        )
