"""FIFO retention for strategy comparisons (10 completed / 5 failed)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.comparison import repository as repo
from app.db.models import Base, StrategyComparisonRow


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/cmp.db", connect_args={"check_same_thread": False}
    )
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
    }
    base.update(over)
    return base


def test_completed_fifo_10(db):
    for i in range(11):
        row = repo.create_running(db, _fields(start_time=i, end_time=i + 1))
        repo.mark_completed(
            db,
            row,
            candle_count=30,
            buy_and_hold_return_pct="0.01",
            buy_and_hold_net_pnl="10",
        )
    rows = list(
        db.scalars(
            select(StrategyComparisonRow).where(StrategyComparisonRow.status == "completed")
        ).all()
    )
    assert len(rows) == 10


def test_failed_fifo_5(db):
    for i in range(6):
        row = repo.create_running(db, _fields(start_time=i, end_time=i + 1))
        repo.mark_failed(db, row, code="insufficient_history", message="short")
    rows = list(
        db.scalars(
            select(StrategyComparisonRow).where(StrategyComparisonRow.status == "failed")
        ).all()
    )
    assert len(rows) == 5


def test_delete_does_not_require_legs_cascade(db):
    row = repo.create_running(db, _fields())
    repo.add_leg(
        db,
        comparison_id=row.id,
        ordinal=0,
        strategy_id="dual_ema",
        strategy_params="{}",
        backtest_run_id="fake-run",
    )
    repo.mark_completed(
        db,
        row,
        candle_count=30,
        buy_and_hold_return_pct="0",
        buy_and_hold_net_pnl="0",
    )
    assert repo.delete_comparison(db, row.id) is True
    assert repo.get_comparison(db, row.id) is None
