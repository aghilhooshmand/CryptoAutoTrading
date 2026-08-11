"""Determinism: identical inputs → identical summary."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.db.models import Base
from app.market_data.models import Candlestick
from app.simulation.money import d


def _candles(n: int = 40) -> list[Candlestick]:
    out = []
    px = 100.0
    start = 1_700_000_000_000
    step = 3_600_000
    for i in range(n):
        px += 0.5 if i < 25 else -0.8
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px),
            )
        )
    return out


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/d.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


def test_identical_runs_identical_summary(db):
    candles = _candles()
    summaries = []
    for _ in range(2):
        fields = {
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "start_time": candles[0].openTime,
            "end_time": candles[-1].openTime + 1,
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
        run = repo.create_running_run(db, fields)
        summaries.append(
            run_engine(
                db,
                run.id,
                candles,
                starting_capital=d("1000"),
                allocated_capital=d("1000"),
                max_position_size=d("1000"),
                fee_rate=d("0.001"),
                slippage_rate=d("0.0005"),
                max_trades=None,
                target_net_profit_amount=None,
                max_session_loss_amount=None,
                wire_shared=True,
            )
        )
    assert summaries[0] == summaries[1]
