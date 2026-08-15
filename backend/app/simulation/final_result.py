"""Frozen Simulation final-result snapshot (Feature 011).

History inspection uses this snapshot as the sole authoritative ending economics
for STOPPED sessions. Backfill is ledger-only — never Feature 002 market quotes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow
from app.simulation.accounting import liquidation_equity, session_net_pnl
from app.simulation.money import as_str, d
from app.simulation.state_machine import SessionState

SOURCE_STOP = "stop"
SOURCE_RECOVERY = "recovery"
SOURCE_BACKFILL = "backfill"
VALID_SOURCES = frozenset({SOURCE_STOP, SOURCE_RECOVERY, SOURCE_BACKFILL})


def _iso_utc(dt: datetime | None = None) -> str:
    value = dt or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _return_pct(net: Decimal, starting: Decimal) -> str:
    if starting == 0:
        return "0"
    return as_str(net / starting)


def build_final_result(
    row: SimulationSessionRow,
    *,
    source: str,
    frozen_at: datetime | None = None,
    mark_price: Decimal | None = None,
    mark_safe: bool = False,
    mark_equity: Decimal | None = None,
) -> dict[str, Any]:
    """Build a FrozenFinalResult dict from session ledger (+ optional stop-time mark)."""
    if source not in VALID_SOURCES:
        raise ValueError(f"invalid finalResult source: {source}")

    starting = d(row.starting_capital)
    cash = d(row.cash)
    flat = row.position_side == "flat" or d(row.position_qty) == 0

    ending: Decimal | None = None
    complete = False
    used_mark: Decimal | None = None

    if flat:
        ending = cash
        complete = True
    elif mark_safe and mark_price is not None and source in (SOURCE_STOP, SOURCE_RECOVERY):
        ending = liquidation_equity(
            cash,
            d(row.position_qty),
            mark_price,
            row.position_side,
            d(row.fee_rate),
            d(row.slippage_rate),
        )
        if ending is not None:
            complete = True
            used_mark = mark_price

    net = session_net_pnl(ending, starting) if complete else None
    return_pct = _return_pct(net, starting) if net is not None else None

    payload = {
        "complete": complete,
        "frozenAt": _iso_utc(frozen_at),
        "source": source,
        "startingCapital": row.starting_capital,
        "endingEquity": as_str(ending) if ending is not None and complete else None,
        "netPnl": as_str(net) if net is not None else None,
        "returnPct": return_pct,
        "cash": row.cash,
        "fees": row.cumulative_fees,
        "slippageCost": row.cumulative_slippage_cost,
        "tradeCount": int(row.trade_count or 0),
        "strategyFillCount": int(row.strategy_fill_count or 0),
        "positionFlattenStatus": row.position_flatten_status or "n/a",
        "stopReason": row.stop_reason,
        "markEquity": as_str(mark_equity) if mark_equity is not None else None,
        "markPrice": as_str(used_mark) if used_mark is not None else None,
    }
    if not complete:
        payload["endingEquity"] = None
        payload["netPnl"] = None
        payload["returnPct"] = None
        # Backfill must never invent market prices
        if source == SOURCE_BACKFILL:
            payload["markEquity"] = None
            payload["markPrice"] = None
    return payload


def serialize_final_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def parse_final_result(raw: str | None) -> dict[str, Any] | None:
    if raw is None or raw == "":
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("final_result_json must be an object")
    return data


def final_result_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        "complete": bool(payload.get("complete")),
        "netPnl": payload.get("netPnl"),
        "returnPct": payload.get("returnPct"),
    }


def persist_final_result(
    db: Session,
    row: SimulationSessionRow,
    *,
    source: str,
    frozen_at: datetime | None = None,
    mark_price: Decimal | None = None,
    mark_safe: bool = False,
    mark_equity: Decimal | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Persist freeze once. Existing JSON is kept unless overwrite=True."""
    existing = parse_final_result(row.final_result_json)
    if existing is not None and not overwrite:
        return existing
    payload = build_final_result(
        row,
        source=source,
        frozen_at=frozen_at,
        mark_price=mark_price,
        mark_safe=mark_safe,
        mark_equity=mark_equity,
    )
    row.final_result_json = serialize_final_result(payload)
    return payload


def ensure_final_result_backfill(db: Session, row: SimulationSessionRow) -> dict[str, Any] | None:
    """Ledger-only backfill for STOPPED rows missing freeze. Never fetches market."""
    if row.state != SessionState.STOPPED.value:
        return parse_final_result(row.final_result_json)
    existing = parse_final_result(row.final_result_json)
    if existing is not None:
        return existing
    payload = persist_final_result(
        db,
        row,
        source=SOURCE_BACKFILL,
        frozen_at=row.stopped_at,
        mark_price=None,
        mark_safe=False,
    )
    db.commit()
    db.refresh(row)
    return payload
