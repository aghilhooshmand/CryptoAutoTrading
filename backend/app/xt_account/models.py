"""Domain models for Real XT account reads (Feature 013)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

PROVENANCE_REAL_XT: Literal["real_xt"] = "real_xt"


class RealXtBalance(BaseModel):
    asset: str
    free: str
    locked: str
    total: Optional[str] = None
    provenance: Literal["real_xt"] = PROVENANCE_REAL_XT


class RealXtOrder(BaseModel):
    orderId: str
    symbol: str
    side: str
    orderType: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    executedQty: Optional[str] = None
    status: str
    updatedAt: Optional[str] = None
    provenance: Literal["real_xt"] = PROVENANCE_REAL_XT


class RealXtBalancesResponse(BaseModel):
    bookProvenance: Literal["real_xt"] = PROVENANCE_REAL_XT
    retrievedAt: str
    balances: list[RealXtBalance] = Field(default_factory=list)


class RealXtOpenOrdersResponse(BaseModel):
    bookProvenance: Literal["real_xt"] = PROVENANCE_REAL_XT
    retrievedAt: str
    orders: list[RealXtOrder] = Field(default_factory=list)


class RealXtOrderStatusResponse(BaseModel):
    bookProvenance: Literal["real_xt"] = PROVENANCE_REAL_XT
    retrievedAt: str
    order: RealXtOrder
