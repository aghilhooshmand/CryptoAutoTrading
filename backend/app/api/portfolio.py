"""Portfolio, holdings & allocations HTTP API (Feature 009)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import session as db_session
from app.portfolio import repository as repo
from app.portfolio import service as svc
from app.portfolio.valuation import fetch_quotes

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


async def _mutate(apply_fn: Callable, reason: str) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        return await svc.snapshot_after(db, reason, lambda: apply_fn(db), fetch_quotes)
    except svc.PortfolioError as err:
        db.rollback()
        _raise(err)
        raise  # pragma: no cover
    finally:
        db.close()


@router.get("")
async def get_portfolio() -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        svc.prepare_read(db)
        quotes = await fetch_quotes(repo.holding_assets(db))
        return svc.build_snapshot(db, quotes)
    finally:
        db.close()


@router.put("/funding")
async def put_funding(body: FundingBody) -> dict[str, Any]:
    return await _mutate(lambda db: svc._apply_funding(db, body.cash), "funding")


@router.post("/allocations", status_code=201)
async def post_allocation(body: CreateAllocationBody) -> dict[str, Any]:
    return await _mutate(
        lambda db: svc._apply_create_allocation(
            db,
            label=body.label,
            reserved_size=body.reservedSize,
            target_ref=body.targetRef,
        ),
        "allocation_create",
    )


@router.patch("/allocations/{allocation_id}")
async def patch_allocation(allocation_id: str, body: PatchAllocationBody) -> dict[str, Any]:
    return await _mutate(
        lambda db: svc._apply_resize_allocation(db, allocation_id, body.reservedSize),
        "allocation_resize",
    )


@router.delete("/allocations/{allocation_id}")
async def delete_allocation(allocation_id: str) -> dict[str, Any]:
    return await _mutate(
        lambda db: svc._apply_release_allocation(db, allocation_id),
        "allocation_release",
    )
