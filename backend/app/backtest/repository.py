"""Backtest SQLite repository with FIFO retention."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import BacktestDecisionRow, BacktestRunRow, BacktestTradeRow

MAX_COMPLETED = 20
MAX_FAILED = 5


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_running_run(db: Session, fields: dict[str, Any]) -> BacktestRunRow:
    now = _utc_now()
    row = BacktestRunRow(
        id=str(uuid.uuid4()),
        status="running",
        created_at=now,
        started_at=now,
        **fields,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def mark_completed(
    db: Session,
    run: BacktestRunRow,
    *,
    summary: dict[str, Any],
    candle_count: int,
) -> BacktestRunRow:
    run.status = "completed"
    run.summary_json = json.dumps(summary)
    run.candle_count = candle_count
    run.completed_at = _utc_now()
    run.error_code = None
    run.error_message = None
    db.add(run)
    db.commit()
    _enforce_completed_fifo(db)
    db.refresh(run)
    return run


def mark_failed(
    db: Session,
    run: BacktestRunRow,
    *,
    code: str,
    message: str,
) -> BacktestRunRow:
    run.status = "failed"
    run.error_code = code
    run.error_message = message
    run.completed_at = _utc_now()
    db.add(run)
    db.commit()
    _enforce_failed_fifo(db)
    db.refresh(run)
    return run


def _enforce_completed_fifo(db: Session) -> None:
    rows = list(
        db.scalars(
            select(BacktestRunRow)
            .where(BacktestRunRow.status == "completed")
            .order_by(BacktestRunRow.completed_at.asc(), BacktestRunRow.id.asc())
        ).all()
    )
    overflow = len(rows) - MAX_COMPLETED
    for row in rows[: max(0, overflow)]:
        _delete_run_cascade(db, row.id)
    db.commit()


def _enforce_failed_fifo(db: Session) -> None:
    rows = list(
        db.scalars(
            select(BacktestRunRow)
            .where(BacktestRunRow.status == "failed")
            .order_by(BacktestRunRow.completed_at.asc(), BacktestRunRow.id.asc())
        ).all()
    )
    overflow = len(rows) - MAX_FAILED
    for row in rows[: max(0, overflow)]:
        _delete_run_cascade(db, row.id)
    db.commit()


def _delete_run_cascade(db: Session, run_id: str) -> None:
    db.execute(delete(BacktestTradeRow).where(BacktestTradeRow.run_id == run_id))
    db.execute(delete(BacktestDecisionRow).where(BacktestDecisionRow.run_id == run_id))
    db.execute(delete(BacktestRunRow).where(BacktestRunRow.id == run_id))


def delete_run(db: Session, run_id: str) -> bool:
    row = db.get(BacktestRunRow, run_id)
    if row is None:
        return False
    if row.status == "running":
        raise RuntimeError("invalid_state")
    _delete_run_cascade(db, run_id)
    db.commit()
    return True


def get_run(db: Session, run_id: str) -> BacktestRunRow | None:
    return db.get(BacktestRunRow, run_id)


def list_runs(db: Session, *, limit: int = 20) -> list[BacktestRunRow]:
    limit = max(1, min(limit, 50))
    return list(
        db.scalars(
            select(BacktestRunRow)
            .order_by(BacktestRunRow.created_at.desc(), BacktestRunRow.id.desc())
            .limit(limit)
        ).all()
    )


def list_trades(db: Session, run_id: str) -> list[BacktestTradeRow]:
    return list(
        db.scalars(
            select(BacktestTradeRow)
            .where(BacktestTradeRow.run_id == run_id)
            .order_by(BacktestTradeRow.created_at.asc(), BacktestTradeRow.id.asc())
        ).all()
    )


def list_decisions(db: Session, run_id: str) -> list[BacktestDecisionRow]:
    return list(
        db.scalars(
            select(BacktestDecisionRow)
            .where(BacktestDecisionRow.run_id == run_id)
            .order_by(BacktestDecisionRow.created_at.asc(), BacktestDecisionRow.id.asc())
        ).all()
    )


def add_decision(
    db: Session,
    run_id: str,
    *,
    signal: str,
    outcome: str,
    candle_open_time: int | None,
    reason_code: str | None = None,
    reason_message: str | None = None,
    fast_ema: str | None = None,
    slow_ema: str | None = None,
) -> BacktestDecisionRow:
    row = BacktestDecisionRow(
        id=str(uuid.uuid4()),
        run_id=run_id,
        created_at=_utc_now(),
        candle_open_time=candle_open_time,
        signal=signal,
        outcome=outcome,
        reason_code=reason_code,
        reason_message=reason_message,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
    )
    db.add(row)
    return row


def add_trade(
    db: Session,
    run_id: str,
    *,
    side: str,
    qty: str,
    reference_price: str,
    fill_price: str,
    fee: str,
    slippage_cost: str,
    notional: str,
    signal_candle_open_time: int | None,
    fill_candle_open_time: int,
    is_end_of_run_flatten: bool = False,
    is_forced_close: bool = False,
    round_trip_id: str | None = None,
) -> BacktestTradeRow:
    row = BacktestTradeRow(
        id=str(uuid.uuid4()),
        run_id=run_id,
        created_at=_utc_now(),
        side=side,
        qty=qty,
        reference_price=reference_price,
        fill_price=fill_price,
        fee=fee,
        slippage_cost=slippage_cost,
        notional=notional,
        signal_candle_open_time=signal_candle_open_time,
        fill_candle_open_time=fill_candle_open_time,
        is_end_of_run_flatten=is_end_of_run_flatten,
        is_forced_close=is_forced_close,
        round_trip_id=round_trip_id,
    )
    db.add(row)
    return row


def has_running(db: Session) -> bool:
    row = db.scalars(
        select(BacktestRunRow).where(BacktestRunRow.status == "running").limit(1)
    ).first()
    return row is not None
