"""HTTP routes for read-only Real XT account inspection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.xt_account.errors import XtPrivateError, http_status_for_code
from app.xt_account.service import XtAccountService, get_xt_account_service

router = APIRouter(prefix="/xt-account", tags=["xt-account"])


def _error(exc: XtPrivateError) -> JSONResponse:
    # Never include credential material in messages (callers must not put secrets in exc.message)
    return JSONResponse(
        status_code=http_status_for_code(exc.code),
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@router.get("/balances", response_model=None)
async def get_balances(
    service: XtAccountService = Depends(get_xt_account_service),
):
    try:
        result = await service.get_balances()
        return result.model_dump(mode="json")
    except XtPrivateError as exc:
        return _error(exc)


@router.get("/open-orders", response_model=None)
async def get_open_orders(
    symbol: str | None = Query(default=None),
    service: XtAccountService = Depends(get_xt_account_service),
):
    try:
        result = await service.list_open_orders(symbol=symbol)
        return result.model_dump(mode="json")
    except XtPrivateError as exc:
        return _error(exc)


@router.get("/orders/{order_id}", response_model=None)
async def get_order_status(
    order_id: str,
    service: XtAccountService = Depends(get_xt_account_service),
):
    try:
        result = await service.get_order(order_id)
        return result.model_dump(mode="json")
    except XtPrivateError as exc:
        return _error(exc)
