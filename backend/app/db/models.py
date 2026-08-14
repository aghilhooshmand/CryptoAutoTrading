"""SQLAlchemy tables for simulation sessions and journals."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SimulationSessionRow(Base):
    __tablename__ = "simulation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(32), default="simulation")
    state: Mapped[str] = mapped_column(String(32), default="CONFIGURED")
    symbol: Mapped[str] = mapped_column(String(64))
    timeframe: Mapped[str] = mapped_column(String(8))
    starting_capital: Mapped[str] = mapped_column(String(64))
    allocated_capital: Mapped[str] = mapped_column(String(64))
    max_position_size: Mapped[str] = mapped_column(String(64))
    target_net_profit_rate: Mapped[str] = mapped_column(String(64))
    max_session_loss_rate: Mapped[str] = mapped_column(String(64))
    target_net_profit_amount: Mapped[str] = mapped_column(String(64))
    max_session_loss_amount: Mapped[str] = mapped_column(String(64))
    max_trades: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    fee_rate: Mapped[str] = mapped_column(String(64))
    slippage_rate: Mapped[str] = mapped_column(String(64))
    strategy_id: Mapped[str] = mapped_column(String(64), default="dual_ema")
    strategy_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    cash: Mapped[str] = mapped_column(String(64))
    position_side: Mapped[str] = mapped_column(String(16), default="flat")
    position_qty: Mapped[str] = mapped_column(String(64), default="0")
    entry_ref_price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_fill_price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_fee: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_slippage_cost: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    strategy_fill_count: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_fees: Mapped[str] = mapped_column(String(64), default="0")
    cumulative_slippage_cost: Mapped[str] = mapped_column(String(64), default="0")
    cumulative_gross_realized: Mapped[str] = mapped_column(String(64), default="0")
    last_processed_candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position_flatten_status: Mapped[str] = mapped_column(String(32), default="n/a")
    unsafe_quote_streak: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DecisionJournalRow(Base):
    __tablename__ = "decision_journal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signal: Mapped[str] = mapped_column(String(8))
    outcome: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fast_ema: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slow_ema: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TradeJournalRow(Base):
    __tablename__ = "trade_journal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    symbol: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[str] = mapped_column(String(64))
    reference_price: Mapped[str] = mapped_column(String(64))
    fill_price: Mapped[str] = mapped_column(String(64))
    fee: Mapped[str] = mapped_column(String(64))
    slippage_cost: Mapped[str] = mapped_column(String(64))
    notional: Mapped[str] = mapped_column(String(64))
    cash_delta: Mapped[str] = mapped_column(String(64))
    is_forced_close: Mapped[bool] = mapped_column(Boolean, default=False)
    candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    symbol: Mapped[str] = mapped_column(String(64))
    timeframe: Mapped[str] = mapped_column(String(8))
    start_time: Mapped[int] = mapped_column(Integer)
    end_time: Mapped[int] = mapped_column(Integer)
    starting_capital: Mapped[str] = mapped_column(String(64))
    allocated_capital: Mapped[str] = mapped_column(String(64))
    max_position_size: Mapped[str] = mapped_column(String(64))
    target_net_profit_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_session_loss_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_net_profit_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_session_loss_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_rate: Mapped[str] = mapped_column(String(64))
    slippage_rate: Mapped[str] = mapped_column(String(64))
    strategy_id: Mapped[str] = mapped_column(String(64), default="dual_ema")
    strategy_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(16), default="manual")
    comparison_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    candle_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyComparisonRow(Base):
    __tablename__ = "strategy_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    symbol: Mapped[str] = mapped_column(String(64))
    timeframe: Mapped[str] = mapped_column(String(8))
    start_time: Mapped[int] = mapped_column(Integer)
    end_time: Mapped[int] = mapped_column(Integer)
    starting_capital: Mapped[str] = mapped_column(String(64))
    allocated_capital: Mapped[str] = mapped_column(String(64))
    max_position_size: Mapped[str] = mapped_column(String(64))
    target_net_profit_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_session_loss_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_net_profit_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_session_loss_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_rate: Mapped[str] = mapped_column(String(64))
    slippage_rate: Mapped[str] = mapped_column(String(64))
    candle_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buy_and_hold_return_pct: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buy_and_hold_net_pnl: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComparisonLegRow(Base):
    __tablename__ = "comparison_legs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    comparison_id: Mapped[str] = mapped_column(String(36), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    strategy_id: Mapped[str] = mapped_column(String(64))
    strategy_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    backtest_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperatorDefaultsRow(Base):
    """Singleton local operator Settings (Feature 008). Fixed id=1."""

    __tablename__ = "operator_defaults"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64))
    timeframe: Mapped[str] = mapped_column(String(8))
    starting_capital: Mapped[str] = mapped_column(String(64))
    allocated_capital: Mapped[str] = mapped_column(String(64))
    max_position_size: Mapped[str] = mapped_column(String(64))
    fee_rate: Mapped[str] = mapped_column(String(64))
    slippage_rate: Mapped[str] = mapped_column(String(64))
    target_net_profit_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_session_loss_rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    strategy_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BacktestDecisionRow(Base):
    __tablename__ = "backtest_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signal: Mapped[str] = mapped_column(String(8))
    outcome: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fast_ema: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slow_ema: Mapped[str | None] = mapped_column(String(64), nullable=True)


class BacktestTradeRow(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[str] = mapped_column(String(64))
    reference_price: Mapped[str] = mapped_column(String(64))
    fill_price: Mapped[str] = mapped_column(String(64))
    fee: Mapped[str] = mapped_column(String(64))
    slippage_cost: Mapped[str] = mapped_column(String(64))
    notional: Mapped[str] = mapped_column(String(64))
    signal_candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fill_candle_open_time: Mapped[int] = mapped_column(Integer)
    is_end_of_run_flatten: Mapped[bool] = mapped_column(Boolean, default=False)
    is_forced_close: Mapped[bool] = mapped_column(Boolean, default=False)
    round_trip_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PortfolioRow(Base):
    """Singleton local portfolio capital (Feature 009). Fixed id=1."""

    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash: Mapped[str] = mapped_column(String(64))
    deployed: Mapped[str] = mapped_column(String(64), default="0")
    realized_pnl: Mapped[str] = mapped_column(String(64), default="0")
    unrealized_pnl: Mapped[str] = mapped_column(String(64), default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortfolioAllocationRow(Base):
    """Capital reservation under the singleton portfolio (Feature 009)."""

    __tablename__ = "portfolio_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    label: Mapped[str] = mapped_column(String(128))
    reserved_size: Mapped[str] = mapped_column(String(64))
    target_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
