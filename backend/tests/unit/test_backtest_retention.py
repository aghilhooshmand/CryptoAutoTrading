"""FIFO retention for completed / failed backtests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.db.models import Base, BacktestRunRow


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/r.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()


def _fields(**over):
    base = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "start_time": 1,
        "end_time": 2,
        "starting_capital": "1000",
        "allocated_capital": "1000",
        "max_position_size": "1000",
        "target_net_profit_rate": None,
        "max_session_loss_rate": None,
        "target_net_profit_amount": None,
        "max_session_loss_amount": None,
        "max_trades": None,
        "fee_rate": "0.001",
        "slippage_rate": "0.0005",
        "strategy_id": "dual_ema_9_21",
    }
    base.update(over)
    return base


def test_completed_fifo_20(db):
    for i in range(21):
        run = repo.create_running_run(db, _fields(start_time=i, end_time=i + 1))
        repo.mark_completed(db, run, summary={"netPnl": "0"}, candle_count=21)
    rows = list(db.scalars(select(BacktestRunRow).where(BacktestRunRow.status == "completed")).all())
    assert len(rows) == 20


def test_failed_fifo_5(db):
    for i in range(6):
        run = repo.create_running_run(db, _fields(start_time=i, end_time=i + 1))
        repo.mark_failed(db, run, code="insufficient_history", message="short")
    rows = list(db.scalars(select(BacktestRunRow).where(BacktestRunRow.status == "failed")).all())
    assert len(rows) == 5
