"""HTTP routes for read-only Real Account inspection (Kraken)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.account.errors import AccountPrivateError, http_status_for_code
from app.account.service import KrakenAccountService, get_account_service

router = APIRouter(prefix="/account", tags=["account"])


def _error(exc: AccountPrivateError) -> JSONResponse:
    return JSONResponse(
        status_code=http_status_for_code(exc.code),
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@router.get("/balances", response_model=None)
async def get_balances(
    service: KrakenAccountService = Depends(get_account_service),
):
    try:
        result = await service.get_balances()
        return result.model_dump(mode="json")
    except AccountPrivateError as exc:
        return _error(exc)


@router.get("/open-orders", response_model=None)
async def get_open_orders(
    venueProductId: str | None = Query(default=None),
    service: KrakenAccountService = Depends(get_account_service),
):
    try:
        result = await service.list_open_orders(venue_product_id=venueProductId)
        return result.model_dump(mode="json")
    except AccountPrivateError as exc:
        return _error(exc)


@router.get("/orders/{venue_order_id}", response_model=None)
async def get_order_status(
    venue_order_id: str,
    service: KrakenAccountService = Depends(get_account_service),
):
    try:
        result = await service.get_order(venue_order_id)
        return result.model_dump(mode="json")
    except AccountPrivateError as exc:
        return _error(exc)
