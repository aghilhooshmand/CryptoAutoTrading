"""Protective take-profit / stop-loss helpers (Feature 025).

Percent config only; absolute levels derived from entry fill.
Trigger on candle high/low; fill price is mode-native (never TP/SL level).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from app.simulation.money import d

REASON_TAKE_PROFIT = "take_profit"
REASON_STOP_LOSS = "stop_loss"


def validate_percents(
    tp: object | None,
    sl: object | None,
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Validate optional TP/SL fractions.

    Returns cleaned ``(take_profit_percent, stop_loss_percent)`` where each
    side is ``None`` when omitted/disabled.

    Raises ``ValueError`` when a provided value is invalid.
    """
    return _optional_tp(tp), _optional_sl(sl)


def _optional_tp(raw: object | None) -> Optional[Decimal]:
    if raw is None or raw == "":
        return None
    try:
        value = d(raw)  # type: ignore[arg-type]
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid takeProfitPercent: {exc}") from exc
    if value <= 0:
        raise ValueError("takeProfitPercent must be > 0 when set")
    return value


def _optional_sl(raw: object | None) -> Optional[Decimal]:
    if raw is None or raw == "":
        return None
    try:
        value = d(raw)  # type: ignore[arg-type]
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid stopLossPercent: {exc}") from exc
    if value <= 0:
        raise ValueError("stopLossPercent must be > 0 when set")
    if value >= 1:
        raise ValueError("stopLossPercent must be < 1 (long stop must stay positive)")
    return value


def derive_levels(
    entry_fill: Decimal,
    tp_pct: Optional[Decimal],
    sl_pct: Optional[Decimal],
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Derive absolute long TP/SL prices from entry fill and percents."""
    if entry_fill <= 0:
        raise ValueError("entry_fill must be > 0")
    tp_price = entry_fill * (Decimal("1") + tp_pct) if tp_pct is not None else None
    sl_price = entry_fill * (Decimal("1") - sl_pct) if sl_pct is not None else None
    if sl_price is not None and sl_price <= 0:
        raise ValueError("stop_loss_price must be > 0")
    return tp_price, sl_price


def evaluate_triggers(
    *,
    candle_open_time: int,
    high: Decimal,
    low: Decimal,
    entry_fill_candle_open_time: int | None,
    tp_price: Optional[Decimal],
    sl_price: Optional[Decimal],
) -> Optional[str]:
    """Return ``stop_loss`` / ``take_profit`` / ``None`` for a closed candle.

    Never evaluates on the entry-fill candle. SL wins if both levels are touched.
    """
    if entry_fill_candle_open_time is not None and candle_open_time == entry_fill_candle_open_time:
        return None
    if sl_price is not None and low <= sl_price:
        return REASON_STOP_LOSS
    if tp_price is not None and high >= tp_price:
        return REASON_TAKE_PROFIT
    return None
