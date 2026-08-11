"""Unit tests for HistoricalExecutionAdapter fills and engine fill timing."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.backtest.execution import HistoricalExecutionAdapter
from app.db.models import BacktestDecisionRow, BacktestTradeRow, Base
from app.market_data.models import Candlestick
from app.simulation.money import d


def test_buy_then_sell_next_open_style():
    adapter = HistoricalExecutionAdapter()
    buy = adapter.buy(
        reference_price=Decimal("100"),
        cash=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        position_side="flat",
    )
    assert buy.ok and buy.fill is not None and buy.qty is not None
    assert buy.fill.fill_price > Decimal("100")
    sell = adapter.sell(
        reference_price=Decimal("110"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        position_side="long",
        position_qty=buy.qty,
    )
    assert sell.ok and sell.fill is not None
    assert sell.fill.fill_price < Decimal("110")


def test_buy_while_long_rejected():
    adapter = HistoricalExecutionAdapter()
    r = adapter.buy(
        reference_price=Decimal("100"),
        cash=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        position_side="long",
    )
    assert not r.ok
    assert r.reason_code == "conflicting_position_state"


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fills.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    yield s
    s.close()


def _candles_crossover(n: int = 60) -> list[Candlestick]:
    """Down then up so Dual EMA produces a BUY after warm-up (clean decimals)."""
    out = []
    start = 1_700_000_000_000
    step = 3_600_000
    # Integer cents to avoid float residue breaking cash cover checks
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


def _create_run(db, candles):
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
    return repo.create_running_run(db, fields)


def test_strategy_fill_uses_next_open(db):
    candles = _candles_crossover()
    run = _create_run(db, candles)
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
    trades = db.query(BacktestTradeRow).filter_by(run_id=run.id).all()
    strategy = [t for t in trades if not t.is_end_of_run_flatten]
    assert strategy, "expected at least one strategy fill"
    for t in strategy:
        assert t.signal_candle_open_time is not None
        assert t.fill_candle_open_time > t.signal_candle_open_time


def test_end_of_run_flatten_at_last_close(db):
    candles = _candles_crossover()
    run = _create_run(db, candles)
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
    flats = (
        db.query(BacktestTradeRow)
        .filter_by(run_id=run.id, is_end_of_run_flatten=True)
        .all()
    )
    # Flatten only if still long at end; otherwise no row — either is OK if position closed
    if flats:
        assert flats[0].fill_candle_open_time == candles[-1].openTime
        assert flats[0].side == "SELL"


def test_missing_next_candle_is_approved_unexecutable(db):
    """Force a BUY only on the last candle so N+1 is missing while still flat."""
    from unittest.mock import MagicMock, patch

    from app.simulation.strategy.base import SignalSide, StrategySignal

    candles = _candles_crossover(25)
    run = _create_run(db, candles)
    last_ot = candles[-1].openTime

    def fake_evaluate(closes):
        if closes and closes[-1].open_time == last_ot:
            return StrategySignal(
                side=SignalSide.BUY,
                candle_open_time=last_ot,
                reason_code="forced_buy",
                fast_ema=Decimal("1"),
                slow_ema=Decimal("0"),
            )
        return StrategySignal(
            side=SignalSide.HOLD,
            candle_open_time=closes[-1].open_time if closes else 0,
            reason_code="hold",
            fast_ema=Decimal("1"),
            slow_ema=Decimal("1"),
        )

    with patch("app.backtest.engine.build_from_stored") as build:
        instance = MagicMock()
        instance.evaluate.side_effect = fake_evaluate
        instance.min_history_candles.return_value = 21
        build.return_value = instance
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

    decisions = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, candle_open_time=last_ot)
        .all()
    )
    assert any(d.outcome == "approved_unexecutable" for d in decisions)
    assert any(d.reason_code == "no_next_candle" for d in decisions)
    assert not any(
        d.outcome == "rejected" and d.reason_code == "no_next_candle" for d in decisions
    )
