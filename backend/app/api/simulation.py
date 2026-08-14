"""Simulation HTTP API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import session as db_session
from app.db.models import DecisionJournalRow, TradeJournalRow
from app.simulation import session_service as svc

router = APIRouter(prefix="/simulation", tags=["simulation"])


class CreateSessionBody(BaseModel):
    mode: str = "simulation"
    symbol: str
    timeframe: str
    startingCapital: str
    allocatedCapital: Optional[str] = None
    maxPositionSize: str
    targetNetProfitRate: str
    maxSessionLossRate: str
    maxTrades: int
    durationSeconds: int
    feeRate: Optional[str] = None
    slippageRate: Optional[str] = None
    strategyId: Optional[str] = None
    strategyParams: Optional[dict[str, Any]] = None
    allocationId: Optional[str] = None
    portfolioMaxLossRate: Optional[str] = None
    portfolioMaxLossAmount: Optional[str] = None
    perSymbolMaxWeight: Optional[str] = None


def _raise(err: svc.SessionError) -> None:
    raise HTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": err.message}},
    )


@router.post("/sessions", status_code=201)
async def create_session(body: CreateSessionBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = svc.create_session(db, body.model_dump(exclude_none=True))
        return await svc.session_to_dict(row)
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = await svc.start_session_async(db, session_id)
        return await svc.session_to_dict(row)
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = await svc.stop_session_async(db, session_id, "manual")
        return await svc.session_to_dict(row)
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.post("/sessions/{session_id}/emergency-stop")
async def emergency_stop(session_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = await svc.stop_session_async(db, session_id, "emergency")
        return await svc.session_to_dict(row)
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/sessions/active")
async def active_session() -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = svc.get_active_session(db)
        return {"session": await svc.session_to_dict(row) if row else None}
    finally:
        db.close()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = svc.get_session(db, session_id)
        return await svc.session_to_dict(row)
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/sessions/{session_id}/decisions")
async def list_decisions(session_id: str, limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        svc.get_session(db, session_id)
        rows = (
            db.query(DecisionJournalRow)
            .filter(DecisionJournalRow.session_id == session_id)
            .order_by(DecisionJournalRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "id": r.id,
                    "createdAt": r.created_at.isoformat().replace("+00:00", "Z"),
                    "candleOpenTime": r.candle_open_time,
                    "signal": r.signal,
                    "outcome": r.outcome,
                    "reasonCode": r.reason_code,
                    "reasonMessage": r.reason_message,
                    "fastEma": r.fast_ema,
                    "slowEma": r.slow_ema,
                }
                for r in rows
            ]
        }
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("/sessions/{session_id}/trades")
async def list_trades(session_id: str, limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        svc.get_session(db, session_id)
        rows = (
            db.query(TradeJournalRow)
            .filter(TradeJournalRow.session_id == session_id)
            .order_by(TradeJournalRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "id": r.id,
                    "createdAt": r.created_at.isoformat().replace("+00:00", "Z"),
                    "symbol": r.symbol,
                    "side": r.side,
                    "qty": r.qty,
                    "referencePrice": r.reference_price,
                    "fillPrice": r.fill_price,
                    "fee": r.fee,
                    "slippageCost": r.slippage_cost,
                    "notional": r.notional,
                    "cashDelta": r.cash_delta,
                    "isForcedClose": r.is_forced_close,
                    "candleOpenTime": r.candle_open_time,
                }
                for r in rows
            ]
        }
    except svc.SessionError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()
