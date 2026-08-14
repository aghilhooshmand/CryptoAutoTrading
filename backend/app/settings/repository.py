"""Singleton OperatorDefaults persistence (Feature 008 + 010)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import OperatorDefaultsRow
from app.settings.starters import SINGLETON_ID
from app.strategy.serialize import dumps_params


def get_row(db: Session) -> OperatorDefaultsRow | None:
    return db.get(OperatorDefaultsRow, SINGLETON_ID)


def upsert_row(
    db: Session,
    *,
    symbol: str,
    timeframe: str,
    starting_capital: str,
    allocated_capital: str,
    max_position_size: str,
    fee_rate: str,
    slippage_rate: str,
    target_net_profit_rate: str | None,
    max_session_loss_rate: str | None,
    max_trades: int | None,
    strategy_id: str,
    strategy_params: dict,
    portfolio_max_loss_rate: str | None = None,
    portfolio_max_loss_amount: str | None = None,
    per_symbol_max_weight: str | None = None,
    preferred_allocation_id: str | None = None,
    updated_at: datetime | None = None,
) -> OperatorDefaultsRow:
    now = updated_at or datetime.now(timezone.utc)
    row = get_row(db)
    if row is None:
        row = OperatorDefaultsRow(id=SINGLETON_ID)
        db.add(row)
    row.symbol = symbol
    row.timeframe = timeframe
    row.starting_capital = starting_capital
    row.allocated_capital = allocated_capital
    row.max_position_size = max_position_size
    row.fee_rate = fee_rate
    row.slippage_rate = slippage_rate
    row.target_net_profit_rate = target_net_profit_rate
    row.max_session_loss_rate = max_session_loss_rate
    row.max_trades = max_trades
    row.strategy_id = strategy_id
    row.strategy_params = dumps_params(strategy_params)
    row.portfolio_max_loss_rate = portfolio_max_loss_rate
    row.portfolio_max_loss_amount = portfolio_max_loss_amount
    row.per_symbol_max_weight = per_symbol_max_weight
    row.preferred_allocation_id = preferred_allocation_id
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
