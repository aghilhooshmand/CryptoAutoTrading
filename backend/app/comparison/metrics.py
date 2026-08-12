"""Map engine summary_json → comparison leg metrics (FR-006)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def leg_metrics_from_summary(
    summary: dict[str, Any],
    *,
    shared_bh_return_pct: str | None = None,
) -> dict[str, Any]:
    """Build comparison-facing leg metrics from a Feature 004 engine summary.

    `fillCount` is the API alias for engine `strategyFillCount`.
    `vsBuyAndHoldReturnPct` = returnPct − buyAndHoldReturnPct (shared when provided).
    """
    bh = shared_bh_return_pct
    if bh is None:
        bh = _as_str(summary.get("buyAndHoldReturnPct"))

    return_pct = _dec(summary.get("returnPct"))
    bh_dec = _dec(bh)
    vs_bh: str | None = None
    if return_pct is not None and bh_dec is not None:
        vs_bh = str(return_pct - bh_dec)

    return {
        "netPnl": _as_str(summary.get("netPnl")),
        "returnPct": _as_str(summary.get("returnPct")),
        "maxDrawdown": _as_str(summary.get("maxDrawdown")),
        "maxDrawdownPct": _as_str(summary.get("maxDrawdownPct")),
        "winRate": _as_str(summary.get("winRate")),
        "roundTripCount": summary.get("roundTripCount"),
        "fillCount": summary.get("strategyFillCount"),
        "totalFees": _as_str(summary.get("totalFees")),
        "totalSlippage": _as_str(summary.get("totalSlippage")),
        "bestTrade": _as_str(summary.get("bestTrade")),
        "worstTrade": _as_str(summary.get("worstTrade")),
        "buyAndHoldReturnPct": bh,
        "vsBuyAndHoldReturnPct": vs_bh,
    }
