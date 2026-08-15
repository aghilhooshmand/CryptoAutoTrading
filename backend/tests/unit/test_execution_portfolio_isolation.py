"""Historical/Backtest must not mutate Portfolio (Feature 012)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.db.models import (
    Base,
    PortfolioAllocationRow,
    PortfolioHoldingRow,
    PortfolioRow,
)
from app.market_data.models import Candlestick
from app.portfolio import repository as portfolio_repo
from app.simulation.money import d


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/iso.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


def _candles_crossover(n: int = 60) -> list[Candlestick]:
    out = []
    start = 1_700_000_000_000
    step = 3_600_000
    px_cents = 12000
    for i in range(n):
        if i < 30:
            px_cents -= 80
        else:
            px_cents += 100
        px = f"{px_cents / 100:.2f}"
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=px,
                high=f"{(px_cents + 100) / 100:.2f}",
                low=f"{(px_cents - 100) / 100:.2f}",
                close=px,
            )
        )
    return out


def _portfolio_fingerprint(db):
    row = db.get(PortfolioRow, 1)
    assert row is not None
    holdings = {
        (h.asset, h.quantity)
        for h in db.scalars(select(PortfolioHoldingRow)).all()
    }
    allocations = {
        (a.id, a.reserved_size, a.label)
        for a in db.scalars(select(PortfolioAllocationRow)).all()
    }
    return (row.cash, row.deployed, holdings, allocations)


def test_backtest_fills_leave_portfolio_unchanged(db):
    portfolio_repo.ensure_portfolio(db)
    before = _portfolio_fingerprint(db)

    candles = _candles_crossover()
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

    db.expire_all()
    assert _portfolio_fingerprint(db) == before
