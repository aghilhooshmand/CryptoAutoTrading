"""Engine tests: warm-up HOLD, determinism, duplicate skip."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.db.models import Base
from app.market_data.models import Candlestick
from app.simulation.money import d


def _candles(n: int, start: int = 1_700_000_000_000, step: int = 3_600_000) -> list[Candlestick]:
    out = []
    px = 100.0
    for i in range(n):
        # Force a crossover later by trending up then down
        if i < 25:
            px += 0.5
        else:
            px -= 0.8
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
    engine = create_engine(f"sqlite:///{tmp_path}/e.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


def _run(db, candles, **kwargs):
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
    summary = run_engine(
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
        **kwargs,
    )
    return run.id, summary


def test_warmup_holds_before_ready(db):
    candles = _candles(30)
    run_id, _summary = _run(db, candles)
    decisions = repo.list_decisions(db, run_id)
    # First many decisions should be HOLD with warmup reason before slow+1
    early = [d for d in decisions if d.candle_open_time is not None][:21]
    assert all(d.outcome == "hold" for d in early)
    assert any(d.reason_code == "warmup" for d in early)


def test_determinism(db):
    candles = _candles(40)
    _id1, s1 = _run(db, candles)
    _id2, s2 = _run(db, candles)
    assert s1 == s2


def test_duplicate_candle_skipped(db):
    candles = _candles(25)
    # Inject duplicate open time
    dup = Candlestick(
        openTime=candles[10].openTime,
        open="1",
        high="1",
        low="1",
        close="1",
    )
    mixed = candles[:11] + [dup] + candles[11:]
    run_id, _ = _run(db, mixed)
    decisions = repo.list_decisions(db, run_id)
    times = [d.candle_open_time for d in decisions if d.candle_open_time is not None]
    assert len(times) == len(set(times))
