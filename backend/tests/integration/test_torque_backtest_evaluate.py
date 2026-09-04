"""Backtest wire for bound Torque phenotypes (Feature 016 US2)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest.engine import run_engine
from app.db.models import Base
from app.market_data.models import Candlestick
from app.simulation.money import d
from app.strategy.base import CandleClose, SignalSide
from app.torque_bind import bind_phenotype, run_bound_backtest
from app.torque_bind.bind import ensure_strategies_registered


def build_fixture_candles(n: int = 80) -> list[Candlestick]:
    """Down then up (integer cents) so Dual EMA / RSI can emit BUY after warm-up."""
    out: list[Candlestick] = []
    start = 1_700_000_000_000
    step = 3_600_000
    px_cents = 12000
    for i in range(n):
        if i < 35:
            px_cents -= 80
        else:
            px_cents += 100
        px = f"{px_cents / 100:.2f}"
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=px,
                high=f"{(px_cents + 50) / 100:.2f}",
                low=f"{(px_cents - 50) / 100:.2f}",
                close=px,
            )
        )
    return out


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/torque.db",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _register():
    ensure_strategies_registered()


def test_run_bound_backtest_replay_identical(db):
    candles = build_fixture_candles()
    strategy = bind_phenotype("rsi(period=14)")
    a = run_bound_backtest(strategy, candles, starting_capital="1000", db=db)
    b = run_bound_backtest(strategy, candles, starting_capital="1000", db=db)
    assert a["netPnl"] == b["netPnl"]
    assert a["tradeCount"] == b["tradeCount"]


def test_composition_differs_from_leaf_signals():
    candles = build_fixture_candles()
    closes = [
        CandleClose(
            open_time=c.openTime,
            close=d(c.close),
            open=d(c.open),
            high=d(c.high),
            low=d(c.low),
        )
        for c in candles
    ]
    leaf = bind_phenotype("dual_ema(fastPeriod=9, slowPeriod=21)")
    combo = bind_phenotype(
        "and(dual_ema(fastPeriod=9, slowPeriod=21), rsi(period=14))"
    )
    diffs = 0
    for i in range(30, len(closes)):
        window = closes[: i + 1]
        if leaf.evaluate(window).side != combo.evaluate(window).side:
            diffs += 1
    assert diffs >= 1


def test_composition_backtest_metrics_differ_from_leaf(db):
    candles = build_fixture_candles()
    leaf = bind_phenotype("dual_ema(fastPeriod=9, slowPeriod=21)")
    combo = bind_phenotype(
        "and(dual_ema(fastPeriod=9, slowPeriod=21), rsi(period=14))"
    )
    leaf_sum = run_bound_backtest(leaf, candles, starting_capital="1000", db=db)
    combo_sum = run_bound_backtest(combo, candles, starting_capital="1000", db=db)
    assert leaf_sum["strategyFillCount"] >= 1 or leaf_sum["tradeCount"] >= 1
    assert (
        leaf_sum["netPnl"] != combo_sum["netPnl"]
        or leaf_sum["tradeCount"] != combo_sum["tradeCount"]
        or leaf_sum["strategyFillCount"] != combo_sum["strategyFillCount"]
    )


def test_run_engine_accepts_bound_strategy_and_uses_controller_risk(db):
    """Bound strategy still goes through Feature 004 path (Controller→Risk fills)."""
    from app.backtest import repository as repo

    candles = build_fixture_candles(60)
    strategy = bind_phenotype("dual_ema(fastPeriod=9, slowPeriod=21)")
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
        "strategy_id": "torque_bound",
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
    # Decisions recorded implies Controller/Risk path ran (not skeleton HOLD-only)
    from app.db.models import BacktestDecisionRow

    rows = db.query(BacktestDecisionRow).filter_by(run_id=run.id).all()
    assert len(rows) >= 1
    outcomes = {r.outcome for r in rows}
    # At least some non-skeleton outcomes when wire_shared
    assert "skeleton" not in outcomes or len(outcomes) > 1
