"""Operator Settings HTTP API (Feature 008)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import session as db_session
from app.settings import service as svc

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsBody(BaseModel):
    symbol: str
    timeframe: str
    startingCapital: str
    allocatedCapital: Optional[str] = None
    maxPositionSize: str
    feeRate: str
    slippageRate: str
    targetNetProfitRate: Optional[str] = None
    maxSessionLossRate: Optional[str] = None
    maxTrades: Optional[int] = None
    strategyId: str
    strategyParams: Optional[dict[str, Any]] = Field(default=None)
    portfolioMaxLossRate: Optional[str] = None
    portfolioMaxLossAmount: Optional[str] = None
    perSymbolMaxWeight: Optional[str] = None
    preferredAllocationId: Optional[str] = None


def _raise(err: svc.SettingsError) -> None:
    raise HTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": err.message}},
    )


@router.get("")
def get_settings() -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.get_settings(db)
    finally:
        db.close()


@router.put("")
def put_settings(body: SettingsBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        payload = body.model_dump(exclude_none=False)
        # Preserve explicit nulls for optional risk fields (unset).
        return svc.put_settings(db, payload)
    except svc.SettingsError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.post("/reset")
def reset_settings() -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.reset_settings(db)
    except svc.SettingsError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()
