"""HTTP routes for normalized market data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.models import ALLOWED_INTERVALS
from app.market_data.service import (
    DEFAULT_CANDLE_LIMIT,
    MarketDataService,
    get_market_data_service,
)

router = APIRouter(prefix="/market", tags=["market"])


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.get("/pairs", response_model=None)
async def get_pairs(
    venue: str | None = Query(default=None),
    service: MarketDataService = Depends(get_market_data_service),
):
    try:
        if venue:
            from app.market_data.service import market_data_service_for

            service = market_data_service_for(venue)
        result = await service.list_pairs()
        return result.model_dump(mode="json")
    except MarketDataAdapterError as exc:
        return _error(502, exc.code, exc.message)


@router.get("/quote", response_model=None)
async def get_quote(
    symbol: str = Query(..., min_length=1),
    venue: str | None = Query(default=None),
    service: MarketDataService = Depends(get_market_data_service),
):
    try:
        if venue:
            from app.market_data.service import market_data_service_for

            service = market_data_service_for(venue, symbol=symbol)
        quote = await service.get_quote(symbol)
        return quote.model_dump(mode="json")
    except UnsupportedSymbolError as exc:
        return _error(404, exc.code, exc.message)
    except MarketDataAdapterError as exc:
        return _error(502, exc.code, exc.message)


@router.get("/candles", response_model=None)
async def get_candles(
    symbol: str = Query(..., min_length=1),
    interval: str = Query(...),
    limit: int = Query(DEFAULT_CANDLE_LIMIT, ge=1, le=1000),
    venue: str | None = Query(default=None),
    service: MarketDataService = Depends(get_market_data_service),
):
    if interval not in ALLOWED_INTERVALS:
        return _error(
            400,
            "invalid_interval",
            "interval must be one of: 1m, 5m, 15m, 1h, 4h, 1d",
        )
    try:
        if venue:
            from app.market_data.service import market_data_service_for

            service = market_data_service_for(venue, symbol=symbol)
        series = await service.get_candles(symbol, interval, limit)
        return series.model_dump(mode="json")
    except UnsupportedSymbolError as exc:
        return _error(404, exc.code, exc.message)
    except MarketDataAdapterError as exc:
        return _error(502, exc.code, exc.message)
    except ValueError as exc:
        return _error(400, "invalid_interval", str(exc))
