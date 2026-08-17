"""Normalize Kraken private payloads to venue-neutral account models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from app.account.models import VenueBalance, VenueOrder
from app.market_data.identity import VENUE_KRAKEN, normalize_asset


def _as_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _as_decimal_string(value: Any) -> Optional[str]:
    amount = _as_decimal(value)
    if amount is None:
        return None
    return format(amount, "f")


def _is_zero(value: Optional[str]) -> bool:
    if value is None:
        return True
    amount = _as_decimal(value)
    return amount is None or amount == 0


def _unix_to_iso(value: Any) -> Optional[str]:
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _free_and_locked(row: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (free, locked, total). locked is None when Kraken does not split."""
    if isinstance(row, dict):
        total = _as_decimal_string(row.get("balance"))
        locked = _as_decimal_string(row.get("hold_trade"))
        if total is None:
            return None, locked, None
        if locked is None:
            return total, None, total
        free_amount = _as_decimal(total) - _as_decimal(locked)
        if free_amount is None:
            return total, locked, total
        if free_amount < 0:
            free_amount = Decimal("0")
        return format(free_amount, "f"), locked, total
    total = _as_decimal_string(row)
    if total is None:
        return None, None, None
    return total, None, total


def normalize_balances(result: Any, *, venue: str = VENUE_KRAKEN) -> list[VenueBalance]:
    if not isinstance(result, dict):
        return []
    out: list[VenueBalance] = []
    for raw_asset, row in result.items():
        asset = normalize_asset(str(raw_asset))
        if not asset:
            continue
        free, locked, total = _free_and_locked(row)
        if free is None:
            continue
        if _is_zero(free) and _is_zero(locked):
            continue
        out.append(
            VenueBalance(
                asset=asset,
                free=free,
                locked=locked,
                total=total,
                venue=venue,
            )
        )
    return out


def normalize_order(
    order_id: str,
    row: Any,
    *,
    venue: str = VENUE_KRAKEN,
) -> Optional[VenueOrder]:
    if not order_id or not isinstance(row, dict):
        return None
    descr = row.get("descr") if isinstance(row.get("descr"), dict) else {}
    pair = str(descr.get("pair") or "").strip()
    side = str(descr.get("type") or row.get("type") or "").strip().upper()
    order_type = str(descr.get("ordertype") or row.get("ordertype") or "").strip() or None
    status = str(row.get("status") or "").strip() or "unknown"
    quantity = _as_decimal_string(row.get("vol"))
    executed = _as_decimal_string(row.get("vol_exec"))
    price = _as_decimal_string(descr.get("price") or row.get("price"))
    updated = _unix_to_iso(row.get("opentm") or row.get("closetm"))
    return VenueOrder(
        venueOrderId=str(order_id),
        venueProductId=pair,
        side=side or "UNKNOWN",
        orderType=order_type,
        quantity=quantity,
        price=price,
        executedQty=executed,
        status=status,
        updatedAt=updated,
        venue=venue,
    )


def normalize_open_orders(
    result: Any,
    *,
    venue: str = VENUE_KRAKEN,
    venue_product_id: str | None = None,
) -> list[VenueOrder]:
    if not isinstance(result, dict):
        return []
    open_map = result.get("open")
    if not isinstance(open_map, dict):
        return []
    wanted = (venue_product_id or "").strip().upper()
    out: list[VenueOrder] = []
    for order_id, row in open_map.items():
        order = normalize_order(str(order_id), row, venue=venue)
        if order is None:
            continue
        if wanted and order.venueProductId.upper() != wanted:
            continue
        out.append(order)
    return out


def normalize_query_orders(result: Any, *, venue: str = VENUE_KRAKEN) -> list[VenueOrder]:
    if not isinstance(result, dict):
        return []
    out: list[VenueOrder] = []
    for order_id, row in result.items():
        order = normalize_order(str(order_id), row, venue=venue)
        if order is not None:
            out.append(order)
    return out
