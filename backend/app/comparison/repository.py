"""Strategy comparison repository with FIFO retention (10 completed / 5 failed)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ComparisonLegRow, StrategyComparisonRow

MAX_COMPLETED = 10
MAX_FAILED = 5


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_running(
    db: Session,
    fields: dict[str, Any],
) -> StrategyComparisonRow:
    now = _utc_now()
    row = StrategyComparisonRow(
        id=str(uuid.uuid4()),
        status="running",
        created_at=now,
        completed_at=None,
        candle_count=None,
        buy_and_hold_return_pct=None,
        buy_and_hold_net_pnl=None,
        error_code=None,
        error_message=None,
        **fields,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_leg(
    db: Session,
    *,
    comparison_id: str,
    ordinal: int,
    strategy_id: str,
    strategy_params: str | None,
    backtest_run_id: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> ComparisonLegRow:
    row = ComparisonLegRow(
        id=str(uuid.uuid4()),
        comparison_id=comparison_id,
        ordinal=ordinal,
        strategy_id=strategy_id,
        strategy_params=strategy_params,
        backtest_run_id=backtest_run_id,
        metrics_json=json.dumps(metrics) if metrics is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_leg(
    db: Session,
    leg: ComparisonLegRow,
    *,
    backtest_run_id: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> ComparisonLegRow:
    if backtest_run_id is not None:
        leg.backtest_run_id = backtest_run_id
    if metrics is not None:
        leg.metrics_json = json.dumps(metrics)
    db.add(leg)
    db.commit()
    db.refresh(leg)
    return leg


def mark_completed(
    db: Session,
    comparison: StrategyComparisonRow,
    *,
    candle_count: int,
    buy_and_hold_return_pct: str,
    buy_and_hold_net_pnl: str,
) -> StrategyComparisonRow:
    comparison.status = "completed"
    comparison.candle_count = candle_count
    comparison.buy_and_hold_return_pct = buy_and_hold_return_pct
    comparison.buy_and_hold_net_pnl = buy_and_hold_net_pnl
    comparison.error_code = None
    comparison.error_message = None
    comparison.completed_at = _utc_now()
    db.add(comparison)
    db.commit()
    _enforce_completed_fifo(db)
    db.refresh(comparison)
    return comparison


def mark_failed(
    db: Session,
    comparison: StrategyComparisonRow,
    *,
    code: str,
    message: str,
    candle_count: int | None = None,
) -> StrategyComparisonRow:
    comparison.status = "failed"
    comparison.error_code = code
    comparison.error_message = message
    if candle_count is not None:
        comparison.candle_count = candle_count
    comparison.completed_at = _utc_now()
    db.add(comparison)
    db.commit()
    _enforce_failed_fifo(db)
    db.refresh(comparison)
    return comparison


def _enforce_completed_fifo(db: Session) -> None:
    rows = list(
        db.scalars(
            select(StrategyComparisonRow)
            .where(StrategyComparisonRow.status == "completed")
            .order_by(
                StrategyComparisonRow.completed_at.asc(),
                StrategyComparisonRow.id.asc(),
            )
        ).all()
    )
    overflow = len(rows) - MAX_COMPLETED
    for row in rows[: max(0, overflow)]:
        _delete_comparison(db, row.id)
    db.commit()


def _enforce_failed_fifo(db: Session) -> None:
    rows = list(
        db.scalars(
            select(StrategyComparisonRow)
            .where(StrategyComparisonRow.status == "failed")
            .order_by(
                StrategyComparisonRow.completed_at.asc(),
                StrategyComparisonRow.id.asc(),
            )
        ).all()
    )
    overflow = len(rows) - MAX_FAILED
    for row in rows[: max(0, overflow)]:
        _delete_comparison(db, row.id)
    db.commit()


def _delete_comparison(db: Session, comparison_id: str) -> None:
    """Delete comparison header + legs only — does not cascade-delete backtest runs."""
    db.execute(delete(ComparisonLegRow).where(ComparisonLegRow.comparison_id == comparison_id))
    db.execute(
        delete(StrategyComparisonRow).where(StrategyComparisonRow.id == comparison_id)
    )


def delete_comparison(db: Session, comparison_id: str) -> bool:
    row = db.get(StrategyComparisonRow, comparison_id)
    if row is None:
        return False
    if row.status == "running":
        raise RuntimeError("invalid_state")
    _delete_comparison(db, comparison_id)
    db.commit()
    return True


def get_comparison(db: Session, comparison_id: str) -> StrategyComparisonRow | None:
    return db.get(StrategyComparisonRow, comparison_id)


def list_legs(db: Session, comparison_id: str) -> list[ComparisonLegRow]:
    return list(
        db.scalars(
            select(ComparisonLegRow)
            .where(ComparisonLegRow.comparison_id == comparison_id)
            .order_by(ComparisonLegRow.ordinal.asc(), ComparisonLegRow.id.asc())
        ).all()
    )


def list_comparisons(db: Session, *, limit: int = 20) -> list[StrategyComparisonRow]:
    limit = max(1, min(limit, 50))
    return list(
        db.scalars(
            select(StrategyComparisonRow)
            .order_by(
                StrategyComparisonRow.created_at.desc(),
                StrategyComparisonRow.id.desc(),
            )
            .limit(limit)
        ).all()
    )


def has_running_comparison(db: Session) -> bool:
    row = db.scalars(
        select(StrategyComparisonRow)
        .where(StrategyComparisonRow.status == "running")
        .limit(1)
    ).first()
    return row is not None
