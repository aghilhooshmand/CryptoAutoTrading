"""Strategy comparison HTTP API (Feature 007)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.comparison import service as svc
from app.db import session as db_session

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


class ComparisonLegBody(BaseModel):
    strategyId: str
    strategyParams: Optional[dict[str, Any]] = None


class CreateComparisonBody(BaseModel):
    symbol: str
    timeframe: str
    startTime: int
    endTime: int
    startingCapital: str
    allocatedCapital: Optional[str] = None
    maxPositionSize: str
    targetNetProfitRate: Optional[str] = None
    maxSessionLossRate: Optional[str] = None
    maxTrades: Optional[int] = None
    feeRate: Optional[str] = None
    slippageRate: Optional[str] = None
    legs: list[ComparisonLegBody]


def _raise(err: svc.ComparisonError) -> None:
    raise HTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": err.message}},
    )


@router.post("", status_code=201)
async def create_comparison(body: CreateComparisonBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        payload = body.model_dump(exclude_none=True)
        try:
            svc.validate_create_body(payload)
        except svc.ComparisonError as err:
            _raise(err)
            raise  # pragma: no cover
        return await svc.create_and_run(db, payload)
    except svc.ComparisonError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("")
def list_comparisons(limit: int = Query(20, ge=1, le=50)) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.list_comparisons_dict(db, limit=limit)
    finally:
        db.close()


@router.get("/{comparison_id}")
def get_comparison(comparison_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.get_comparison_dict(db, comparison_id)
    except svc.ComparisonError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.delete("/{comparison_id}", status_code=204)
def delete_comparison(comparison_id: str) -> None:
    db = db_session.SessionLocal()
    try:
        svc.delete_comparison(db, comparison_id)
    except svc.ComparisonError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()
