"""Portfolio & allocations HTTP API (Feature 009)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import session as db_session
from app.portfolio import service as svc

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class FundingBody(BaseModel):
    cash: str


class CreateAllocationBody(BaseModel):
    label: str
    reservedSize: str
    targetRef: Optional[str] = None


class PatchAllocationBody(BaseModel):
    reservedSize: str


def _raise(err: svc.PortfolioError) -> None:
    raise HTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": err.message}},
    )


@router.get("")
def get_portfolio() -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.build_snapshot(db)
    finally:
        db.close()


@router.put("/funding")
def put_funding(body: FundingBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.set_funding(db, body.cash)
    except svc.PortfolioError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.post("/allocations", status_code=201)
def post_allocation(body: CreateAllocationBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.create_allocation(
            db,
            label=body.label,
            reserved_size=body.reservedSize,
            target_ref=body.targetRef,
        )
    except svc.PortfolioError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.patch("/allocations/{allocation_id}")
def patch_allocation(allocation_id: str, body: PatchAllocationBody) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.resize_allocation(db, allocation_id, body.reservedSize)
    except svc.PortfolioError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.delete("/allocations/{allocation_id}")
def delete_allocation(allocation_id: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return svc.release_allocation(db, allocation_id)
    except svc.PortfolioError as err:
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()
