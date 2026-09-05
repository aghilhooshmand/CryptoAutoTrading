"""Frozen torque_phenotype Backtest path (Feature 019 US3)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.db.models import Base
from app.market_data.models import Candlestick
from app.simulation.money import d
from app.strategy.registry import build_from_stored, is_known_strategy_id
from app.torque_bind.bind import ensure_strategies_registered


def _candles(n: int = 60) -> list[Candlestick]:
    out = []
    start = 1_700_000_000_000
    step = 3_600_000
    px_cents = 12000
    for i in range(n):
        px_cents += 80 if i >= 30 else -60
        px = f"{px_cents / 100:.2f}"
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=px,
                high=f"{(px_cents + 40) / 100:.2f}",
                low=f"{(px_cents - 40) / 100:.2f}",
                close=px,
            )
        )
    return out


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/uge_bt.db",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


def test_torque_phenotype_registered_and_backtests(db):
    import app.uge_search.phenotype_strategy  # noqa: F401

    ensure_strategies_registered()
    assert is_known_strategy_id("torque_phenotype")
    phenotype = "dual_ema(fastPeriod=9, slowPeriod=21)"
    strategy = build_from_stored("torque_phenotype", {"phenotype": phenotype})
    candles = _candles()
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
        "strategy_id": "torque_phenotype",
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
        strategy=strategy,
    )
    assert "netPnl" in summary
