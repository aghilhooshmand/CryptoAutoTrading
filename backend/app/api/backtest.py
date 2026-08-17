"""Backtest HTTP API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.backtest import service as svc
from app.db import session as db_session

router = APIRouter(prefix="/backtest", tags=["backtest"])


class CreateBacktestBody(BaseModel):
    symbol: Optional[str] = None
    venue: Optional[str] = None
    baseAsset: Optional[str] = None
    quoteAsset: Optional[str] = None
    canonicalSymbol: Optional[str] = None
    venueProductId: Optional[str] = None
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
    strategyId: Optional[str] = None
    strategyParams: Optional[dict[str, Any]] = None
    takeProfitPercent: Optional[str] = None
    stopLossPercent: Optional[str] = None


def _raise(err: svc.BacktestError) -> None:
    raise HTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": err.message}},
    )


@router.post("/runs", status_code=201)
async def create_run(body: CreateBacktestBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        # Pre-accept validation (no durable row on invalid_config / oversized estimate)
        try:
            svc.validate_config(body.model_dump(exclude_none=True))
        except svc.BacktestError as err:
            _raise(err)
            raise  # pragma: no cover
        return await svc.create_and_run(db, body.model_dump(exclude_none=True), wire_shared=True)
    except svc.BacktestError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=50),
    includeComparisonOrigin: bool = Query(False),
) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.list_runs_dict(
            db, limit=limit, include_comparison_origin=includeComparisonOrigin
        )
    finally:
        db.close()


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.get_run_dict(db, run_id)
    except svc.BacktestError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/runs/{run_id}/trades")
def get_trades(run_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.trades_dict(db, run_id)
    except svc.BacktestError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/runs/{run_id}/decisions")
def get_decisions(run_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.decisions_dict(db, run_id)
    except svc.BacktestError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str) -> None:
    db = db_session.SessionLocal()
    try:
        svc.delete_run(db, run_id)
    except svc.BacktestError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()
