"""Strategy registry HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.strategy import dual_ema as _dual_ema  # noqa: F401
from app.strategy.registry import to_api_list

router = APIRouter(tags=["strategies"])


@router.get("/strategies")
def list_strategies() -> dict[str, Any]:
    return {"strategies": to_api_list()}
