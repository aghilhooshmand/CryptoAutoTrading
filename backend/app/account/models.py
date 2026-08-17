"""Venue-neutral private-account models (Feature 013 Kraken amendment)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.market_data.identity import VENUE_KRAKEN


class VenueBalance(BaseModel):
    asset: str
    free: str
    locked: Optional[str] = None
    total: Optional[str] = None
    venue: str = VENUE_KRAKEN


class VenueOrder(BaseModel):
    venueOrderId: str
    venueProductId: str
    side: str
    orderType: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    executedQty: Optional[str] = None
    status: str
    updatedAt: Optional[str] = None
    venue: str = VENUE_KRAKEN


class AccountBalancesResponse(BaseModel):
    venue: str = VENUE_KRAKEN
    retrievedAt: str
    balances: list[VenueBalance] = Field(default_factory=list)


class AccountOpenOrdersResponse(BaseModel):
    venue: str = VENUE_KRAKEN
    retrievedAt: str
    orders: list[VenueOrder] = Field(default_factory=list)


class AccountOrderStatusResponse(BaseModel):
    venue: str = VENUE_KRAKEN
    retrievedAt: str
    order: VenueOrder
