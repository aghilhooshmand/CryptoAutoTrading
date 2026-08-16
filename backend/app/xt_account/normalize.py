"""Normalize XT private payloads to Real XT domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from app.xt_account.models import RealXtBalance, RealXtOrder


def _as_decimal_string(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError):
        return None


def _is_zero(value: Optional[str]) -> bool:
    if value is None:
        return True
    try:
        return Decimal(value) == 0
    except InvalidOperation:
        return True


def _ms_to_iso(ms: Any) -> Optional[str]:
    if ms is None or ms == "":
        return None
    try:
        dt = datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def normalize_balances(result: Any) -> list[RealXtBalance]:
    """Map XT /v4/balances result; omit zero free and zero locked."""
    assets: list[Any]
    if isinstance(result, dict):
        assets = result.get("assets") or []
    elif isinstance(result, list):
        assets = result
    else:
        assets = []

    out: list[RealXtBalance] = []
    for row in assets:
        if not isinstance(row, dict):
            continue
        asset = str(row.get("currency") or "").strip().lower()
        if not asset:
            continue
        free = _as_decimal_string(row.get("availableAmount"))
        locked = _as_decimal_string(row.get("frozenAmount"))
        if free is None and locked is None:
            continue
        free_s = free if free is not None else "0"
        locked_s = locked if locked is not None else "0"
        if _is_zero(free_s) and _is_zero(locked_s):
            continue
        total = _as_decimal_string(row.get("totalAmount"))
        if total is None and free is not None and locked is not None:
            try:
                total = format(Decimal(free_s) + Decimal(locked_s), "f")
            except InvalidOperation:
                total = None
        out.append(
            RealXtBalance(
                asset=asset,
                free=free_s,
                locked=locked_s,
                total=total,
            )
        )
    return out


def normalize_order(row: Any) -> Optional[RealXtOrder]:
    if not isinstance(row, dict):
        return None
    order_id = row.get("orderId")
    if order_id is None or order_id == "":
        return None
    symbol = str(row.get("symbol") or "").strip()
    side = str(row.get("side") or "").strip()
    status = str(row.get("state") or row.get("status") or "").strip()
    if not symbol or not side or not status:
        return None
    updated = _ms_to_iso(row.get("updatedTime")) or _ms_to_iso(row.get("time"))
    return RealXtOrder(
        orderId=str(order_id),
        symbol=symbol,
        side=side,
        orderType=str(row["type"]) if row.get("type") is not None else None,
        quantity=_as_decimal_string(row.get("origQty")),
        price=_as_decimal_string(row.get("price")),
        executedQty=_as_decimal_string(row.get("executedQty")),
        status=status,
        updatedAt=updated,
    )


def normalize_open_orders(result: Any) -> list[RealXtOrder]:
    rows: list[Any]
    if isinstance(result, list):
        rows = result
    elif isinstance(result, dict):
        rows = result.get("items") or result.get("orders") or []
    else:
        rows = []
    out: list[RealXtOrder] = []
    for row in rows:
        order = normalize_order(row)
        if order is not None:
            out.append(order)
    return out
