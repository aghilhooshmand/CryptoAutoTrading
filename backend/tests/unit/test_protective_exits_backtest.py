"""Backtest protective TP/SL exits (Feature 025 US1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import EngineState, _apply_strategy_fill, _flatten, run_engine
from app.backtest.execution import HistoricalExecutionAdapter
from app.db.models import Base, BacktestDecisionRow, BacktestTradeRow
from app.execution.tpsl import REASON_STOP_LOSS, REASON_TAKE_PROFIT, evaluate_triggers
from app.market_data.models import Candlestick
from app.simulation.accounting import buy_fill
from app.simulation.money import d
from app.strategy.base import CandleClose, SignalSide, StrategySignal


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/bt.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


def _c(ot: int, o: str, h: str, l: str, cl: str) -> Candlestick:
    return Candlestick(openTime=ot, open=o, high=h, low=l, close=cl)


def _run_fields(**extra):
    base = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "start_time": 1,
        "end_time": 99,
        "starting_capital": "1000",
        "allocated_capital": "1000",
        "max_position_size": "1000",
        "fee_rate": "0",
        "slippage_rate": "0",
        "strategy_id": "dual_ema",
        "strategy_params": None,
        "take_profit_percent": "0.02",
        "stop_loss_percent": "0.01",
        "max_trades": 10,
        "target_net_profit_rate": None,
        "max_session_loss_rate": None,
        "target_net_profit_amount": None,
        "max_session_loss_amount": None,
    }
    base.update(extra)
    return base


class _ScriptedStrategy:
    """BUY once on first bar, then HOLD — lets protective exits own the close."""

    def __init__(self) -> None:
        self._bought = False

    def min_history_candles(self) -> int:
        return 1

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        last = closes[-1]
        if not self._bought:
            self._bought = True
            return StrategySignal(
                side=SignalSide.BUY,
                candle_open_time=last.open_time,
                fast_ema=None,
                slow_ema=None,
            )
        return StrategySignal(
            side=SignalSide.HOLD,
            candle_open_time=last.open_time,
            fast_ema=None,
            slow_ema=None,
            reason_code="hold",
        )


def test_backtest_take_profit_fills_at_next_open_not_tp_level(db):
    run = repo.create_running_run(db, _run_fields(stop_loss_percent=None))
    # bar0 signal BUY → fill at bar1 open 100
    # bar1 is entry fill candle → skip TP even if high spikes
    # bar2 high crosses TP 102 → sell at bar3 open 110 (not 102)
    candles = [
        _c(1000, "100", "100", "100", "100"),
        _c(2000, "100", "200", "100", "100"),
        _c(3000, "101", "105", "101", "104"),
        _c(4000, "110", "111", "109", "110"),
    ]
    scripted = _ScriptedStrategy()
    with patch("app.backtest.engine.build_from_stored", return_value=scripted):
        summary = run_engine(
            db,
            run.id,
            candles,
            starting_capital=Decimal("1000"),
            allocated_capital=Decimal("1000"),
            max_position_size=Decimal("1000"),
            fee_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            max_trades=10,
            target_net_profit_amount=None,
            max_session_loss_amount=None,
            take_profit_percent=Decimal("0.02"),
            stop_loss_percent=None,
        )
    sell = (
        db.query(BacktestTradeRow)
        .filter_by(run_id=run.id, side="SELL", is_forced_close=True)
        .one()
    )
    assert d(sell.reference_price) == Decimal("110")
    assert d(sell.fill_price) == Decimal("110")
    assert d(sell.fill_price) != Decimal("102")
    decision = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, reason_code=REASON_TAKE_PROFIT)
        .one()
    )
    assert decision.outcome == "forced"
    # BUY counted; protective SELL did not
    assert summary["strategyFillCount"] == 1


def test_backtest_entry_bar_skip_and_stop_loss_next_open(db):
    run = repo.create_running_run(db, _run_fields(take_profit_percent=None))
    state = EngineState(
        cash=Decimal("1000"),
        take_profit_percent=None,
        stop_loss_percent=Decimal("0.01"),
    )
    fill = buy_fill(Decimal("1"), Decimal("100"), Decimal("0"), Decimal("0"))
    _apply_strategy_fill(
        db,
        run.id,
        state,
        side="BUY",
        qty=Decimal("1"),
        fill=fill,
        signal_open=1000,
        fill_open=2000,
    )
    assert state.stop_loss_price == Decimal("99")
    assert state.entry_fill_candle_open_time == 2000
    assert (
        evaluate_triggers(
            candle_open_time=2000,
            high=Decimal("200"),
            low=Decimal("1"),
            entry_fill_candle_open_time=state.entry_fill_candle_open_time,
            tp_price=state.take_profit_price,
            sl_price=state.stop_loss_price,
        )
        is None
    )
    assert (
        evaluate_triggers(
            candle_open_time=3000,
            high=Decimal("100"),
            low=Decimal("98"),
            entry_fill_candle_open_time=state.entry_fill_candle_open_time,
            tp_price=state.take_profit_price,
            sl_price=state.stop_loss_price,
        )
        == REASON_STOP_LOSS
    )
    before = state.strategy_fill_count
    _flatten(
        db,
        run.id,
        state,
        HistoricalExecutionAdapter(),
        reference=Decimal("97"),
        fill_open_time=4000,
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        forced=True,
        end_of_run=False,
        reason=REASON_STOP_LOSS,
    )
    db.flush()
    assert state.strategy_fill_count == before
    trade = (
        db.query(BacktestTradeRow)
        .filter_by(run_id=run.id, side="SELL", is_forced_close=True)
        .one()
    )
    assert d(trade.fill_price) == Decimal("97")
    assert d(trade.fill_price) != Decimal("99")


def test_backtest_protective_no_next_candle_fail_closed(db):
    run = repo.create_running_run(db, _run_fields(stop_loss_percent=None))
    # BUY on 1000 → fill open 2000; bar 2000 is last → if TP somehow triggered later N/A.
    # Trigger TP on last bar with no following candle.
    candles = [
        _c(1000, "100", "100", "100", "100"),
        _c(2000, "100", "100", "100", "100"),
        _c(3000, "101", "105", "101", "104"),
    ]
    scripted = _ScriptedStrategy()
    with patch("app.backtest.engine.build_from_stored", return_value=scripted):
        run_engine(
            db,
            run.id,
            candles,
            starting_capital=Decimal("1000"),
            allocated_capital=Decimal("1000"),
            max_position_size=Decimal("1000"),
            fee_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            max_trades=10,
            target_net_profit_amount=None,
            max_session_loss_amount=None,
            take_profit_percent=Decimal("0.02"),
            stop_loss_percent=None,
        )
    unexec = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, reason_code="no_next_candle")
        .all()
    )
    assert any("Protective" in (d.reason_message or "") for d in unexec)
    # Still long until end-of-run flatten
    end_flat = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, reason_code="end_of_run_flatten")
        .all()
    )
    assert end_flat
