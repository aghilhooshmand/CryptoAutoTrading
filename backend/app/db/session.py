"""SQLite engine and session factory for simulation / backtest domain state."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data"
_DEFAULT_PATH = _DEFAULT_DIR / "simulation.db"


def db_path() -> Path:
    # Optional BACKTEST_DB_PATH: when set, shared domain DB uses that path
    # (Feature 004). Otherwise SIMULATION_DB_PATH / default simulation.db.
    raw = os.environ.get("BACKTEST_DB_PATH") or os.environ.get("SIMULATION_DB_PATH")
    if raw:
        return Path(raw)
    return _DEFAULT_PATH


def make_engine(url: str | None = None):
    if url is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    return create_engine(url, connect_args={"check_same_thread": False})


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Session:
    return SessionLocal()


def init_db() -> None:
    from sqlalchemy import inspect, text

    from app.db import models  # noqa: F401
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    # SQLite create_all does not add columns to existing tables.
    _ensure_column(engine, "simulation_sessions", "strategy_params", "TEXT")
    _ensure_column(engine, "backtest_runs", "strategy_params", "TEXT")
    _ensure_column(engine, "backtest_runs", "origin", "TEXT DEFAULT 'manual'")
    _ensure_column(engine, "backtest_runs", "comparison_id", "TEXT")
    _ensure_column(engine, "portfolio", "fill_apply_warning", "TEXT")
    # Feature 010 session risk fields
    for col, typ in (
        ("allocation_id", "TEXT"),
        ("portfolio_max_loss_rate", "TEXT"),
        ("portfolio_max_loss_amount", "TEXT"),
        ("portfolio_loss_baseline_kind", "TEXT"),
        ("portfolio_loss_baseline_value", "TEXT"),
        ("per_symbol_max_weight", "TEXT"),
        ("decision_log_mode", "TEXT"),
        ("final_result_json", "TEXT"),
        # Feature 014 recovery fields
        ("recovery_reason", "TEXT"),
        ("recovery_detail", "TEXT"),
        ("last_recovery_at", "DATETIME"),
        # Feature 025 protective TP/SL
        ("take_profit_percent", "TEXT"),
        ("stop_loss_percent", "TEXT"),
        ("take_profit_price", "TEXT"),
        ("stop_loss_price", "TEXT"),
        ("entry_fill_candle_open_time", "INTEGER"),
        # Feature 015 Controlled Real
        ("xt_order_id", "TEXT"),
        ("real_reconcile_status", "TEXT"),
        ("real_submit_status", "TEXT"),
        ("venue_order_id", "TEXT"),
        ("venue", "TEXT"),
        ("base_asset", "TEXT"),
        ("quote_asset", "TEXT"),
        ("canonical_symbol", "TEXT"),
        ("venue_product_id", "TEXT"),
    ):
        _ensure_column(engine, "simulation_sessions", col, typ)
    for col, typ in (
        ("take_profit_percent", "TEXT"),
        ("stop_loss_percent", "TEXT"),
        ("venue", "TEXT"),
        ("base_asset", "TEXT"),
        ("quote_asset", "TEXT"),
        ("canonical_symbol", "TEXT"),
        ("venue_product_id", "TEXT"),
    ):
        _ensure_column(engine, "backtest_runs", col, typ)
    for col, typ in (
        ("portfolio_max_loss_rate", "TEXT"),
        ("portfolio_max_loss_amount", "TEXT"),
        ("per_symbol_max_weight", "TEXT"),
        ("preferred_allocation_id", "TEXT"),
        ("decision_log_mode", "TEXT"),
        # Feature 025 protective TP/SL defaults
        ("take_profit_percent", "TEXT"),
        ("stop_loss_percent", "TEXT"),
        ("venue", "TEXT"),
        ("base_asset", "TEXT"),
        ("quote_asset", "TEXT"),
        ("canonical_symbol", "TEXT"),
        ("venue_product_id", "TEXT"),
    ):
        _ensure_column(engine, "operator_defaults", col, typ)
    for col, typ in (
        ("venue", "TEXT"),
        ("base_asset", "TEXT"),
        ("quote_asset", "TEXT"),
        ("canonical_symbol", "TEXT"),
        ("venue_product_id", "TEXT"),
    ):
        _ensure_column(engine, "strategy_comparisons", col, typ)
    _ensure_column(engine, "portfolio", "quote_asset", "TEXT")
    _ensure_column(engine, "real_order_reconcile", "venue_order_id", "TEXT")
    # Feature 014: journal uniqueness for existing SQLite DBs (create_all alone is insufficient).
    _ensure_unique_index(
        engine,
        "uq_trade_journal_session_candle_forced",
        "trade_journal",
        "(session_id, candle_open_time, is_forced_close)",
    )
    _ensure_unique_index(
        engine,
        "uq_decision_journal_session_candle",
        "decision_journal",
        "(session_id, candle_open_time)",
    )
    # Feature 009: leftover portfolio.cash → usdt holding; provenance rewrite.
    from app.portfolio.repository import migrate_cash_to_usdt, migrate_provenance

    db = SessionLocal()
    try:
        migrate_cash_to_usdt(db)
        migrate_provenance(db)
        db.commit()
    finally:
        db.close()


def _ensure_column(eng, table: str, column: str, coltype: str) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(eng)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column in existing:
        return
    with eng.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def _ensure_unique_index(eng, name: str, table: str, columns_sql: str) -> None:
    """CREATE UNIQUE INDEX IF NOT EXISTS for journal idempotency on existing DBs."""
    from sqlalchemy import inspect, text

    insp = inspect(eng)
    if table not in insp.get_table_names():
        return
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name in existing:
        return
    with eng.begin() as conn:
        conn.execute(
            text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} {columns_sql}")
        )
