"""Offline gap skip + watermark advance (Feature 014 FR-010)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import SimulationSessionRow, SkippedGapAuditRow
from app.market_data.public_retry import PublicRetryExhausted, with_public_retry
from app.market_data.service import get_market_data_service
from app.simulation.reconcile import GATE_GAP

logger = logging.getLogger(__name__)

REASON_OFFLINE_GAP_SKIP = "offline_gap_skip"

_INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


async def _fetch_closed_open_times(row: SimulationSessionRow) -> list[int]:
    from app.simulation.clock import SystemClock

    clock = SystemClock()
    interval = _INTERVAL_SECONDS.get(row.timeframe)
    if interval is None:
        raise ValueError(f"Unsupported timeframe: {row.timeframe}")

    async def _call():
        return await get_market_data_service().get_candles(row.symbol, row.timeframe)

    series = await with_public_retry(_call)
    now_ms = int(clock.now().timestamp() * 1000)
    out: list[int] = []
    for c in series.candles:
        if c.openTime + interval * 1000 <= now_ms:
            out.append(c.openTime)
    return out


async def apply_offline_gap_skip(
    db: Session,
    row: SimulationSessionRow,
    *,
    market_candles_open_times: list[int] | None = None,
) -> tuple[bool, str | None]:
    """Advance watermark past offline closed candles without inventing fills.

    Returns (ok, error_code). On success may write SkippedGapAuditRow.
    """
    watermark = row.last_processed_candle_open_time

    if market_candles_open_times is None:
        try:
            open_times = await _fetch_closed_open_times(row)
        except (PublicRetryExhausted, Exception):  # noqa: BLE001
            logger.info(
                "gap_skip unresolvable session_id=%s watermark=%s",
                row.id,
                watermark,
            )
            return False, GATE_GAP
    else:
        open_times = list(market_candles_open_times)

    if not open_times:
        # Watermark set but no closed candles → cannot prove offline gap bounds.
        if watermark is not None:
            logger.info(
                "gap_skip unresolvable empty_history session_id=%s watermark=%s",
                row.id,
                watermark,
            )
            return False, GATE_GAP
        # No watermark and no candles: nothing to skip yet.
        return True, None

    if watermark is None:
        newer = open_times
    else:
        newer = [t for t in open_times if t > watermark]

    if not newer:
        return True, None

    latest = max(newer)
    prior = watermark
    now = datetime.now(timezone.utc)
    row.last_processed_candle_open_time = latest
    row.updated_at = now
    db.add(
        SkippedGapAuditRow(
            id=str(uuid.uuid4()),
            session_id=row.id,
            from_open_time=prior,
            to_open_time=latest,
            reason=REASON_OFFLINE_GAP_SKIP,
            recorded_at=now,
        )
    )
    logger.info(
        "gap_skip session_id=%s from=%s to=%s",
        row.id,
        prior,
        latest,
    )
    return True, None
