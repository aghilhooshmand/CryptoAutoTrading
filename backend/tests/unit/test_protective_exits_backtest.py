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


def test_backtest_protective_goes_through_controller_and_risk(db):
    """FR-003: protective close must call Controller and Risk before flatten."""
    run = repo.create_running_run(db, _run_fields(stop_loss_percent=None))
    candles = [
        _c(1000, "100", "100", "100", "100"),
        _c(2000, "100", "100", "100", "100"),
        _c(3000, "100", "103", "100", "102"),
        _c(4000, "110", "110", "110", "110"),
    ]
    scripted = _ScriptedStrategy()
    with (
        patch("app.backtest.engine.build_from_stored", return_value=scripted),
        patch(
            "app.backtest.engine.TradingController.review",
            wraps=None,
        ) as ctrl_review,
        patch(
            "app.backtest.engine.RiskManager.review",
            wraps=None,
        ) as risk_review,
    ):
        from app.simulation.control.controller import ControlDecision
        from app.simulation.control.risk import RiskDecision

        ctrl_review.return_value = ControlDecision(True)
        risk_review.return_value = RiskDecision(True)

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

    # Bound method mocks receive (state, signal) / (signal, ctx) without self.
    sell_ctrl = [
        c
        for c in ctrl_review.call_args_list
        if len(c.args) >= 2
        and getattr(c.args[1], "side", None) == SignalSide.SELL
        and getattr(c.args[1], "reason_code", None) == REASON_TAKE_PROFIT
    ]
    sell_risk = [
        c
        for c in risk_review.call_args_list
        if len(c.args) >= 1
        and getattr(c.args[0], "side", None) == SignalSide.SELL
        and getattr(c.args[0], "reason_code", None) == REASON_TAKE_PROFIT
    ]
    assert sell_ctrl, "Controller.review was not called for protective SELL"
    assert sell_risk, "RiskManager.review was not called for protective SELL"
    forced = (
        db.query(BacktestTradeRow)
        .filter_by(run_id=run.id, side="SELL", is_forced_close=True)
        .one()
    )
    assert d(forced.fill_price) == Decimal("110")


def test_backtest_profit_target_beats_take_profit(db):
    """FR-006: Risk session profit-target stop precedes protective TP."""
    run = repo.create_running_run(
        db,
        _run_fields(
            stop_loss_percent=None,
            target_net_profit_amount="1",
            max_session_loss_amount=None,
        ),
    )
    # BUY → fill 100; later bar high crosses TP and close marks large unrealized profit
    candles = [
        _c(1000, "100", "100", "100", "100"),
        _c(2000, "100", "100", "100", "100"),
        _c(3000, "100", "200", "100", "180"),
        _c(4000, "180", "180", "180", "180"),
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
            target_net_profit_amount=Decimal("1"),
            max_session_loss_amount=None,
            take_profit_percent=Decimal("0.02"),
            stop_loss_percent=None,
        )
    tp_decisions = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, reason_code=REASON_TAKE_PROFIT)
        .count()
    )
    assert tp_decisions == 0
    profit_stops = (
        db.query(BacktestDecisionRow)
        .filter_by(run_id=run.id, reason_code="profit_target")
        .count()
    )
    assert profit_stops >= 1
    assert summary["strategyFillCount"] == 1  # BUY only; forced stop did not increment


def test_backtest_repeated_cycles_cash_matches_fills(db):
    """SC-004: ≥3 BUY→TP cycles leave cash equal to starting + sum(cash deltas)."""

    class _CycleStrategy:
        def min_history_candles(self) -> int:
            return 1

        def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
            last = closes[-1]
            # Alternate BUY when flat — engine state is not visible; buy on even bars
            # Use close == 100 as buy cue and never sell (protective owns exits).
            if last.close == Decimal("100") and last.high == Decimal("100"):
                return StrategySignal(SignalSide.BUY, last.open_time, None, None)
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "hold")

    run = repo.create_running_run(db, _run_fields(stop_loss_percent=None, max_trades=20))
    candles: list[Candlestick] = []
    t = 1000
    for _ in range(3):
        candles.append(_c(t, "100", "100", "100", "100"))  # BUY signal
        t += 1000
        candles.append(_c(t, "100", "100", "100", "100"))  # fill / entry bar
        t += 1000
        candles.append(_c(t, "100", "103", "100", "102"))  # TP trigger
        t += 1000
        candles.append(_c(t, "100", "100", "100", "100"))  # next-open protective fill
        t += 1000
    with patch("app.backtest.engine.build_from_stored", return_value=_CycleStrategy()):
        summary = run_engine(
            db,
            run.id,
            candles,
            starting_capital=Decimal("1000"),
            allocated_capital=Decimal("1000"),
            max_position_size=Decimal("1000"),
            fee_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            max_trades=20,
            target_net_profit_amount=None,
            max_session_loss_amount=None,
            take_profit_percent=Decimal("0.02"),
            stop_loss_percent=None,
        )
    trades = (
        db.query(BacktestTradeRow)
        .filter_by(run_id=run.id)
        .order_by(BacktestTradeRow.fill_candle_open_time.asc())
        .all()
    )
    protective = [t for t in trades if t.is_forced_close and t.side == "SELL"]
    buys = [t for t in trades if t.side == "BUY"]
    assert len(buys) >= 3
    assert len(protective) >= 3
    assert summary["strategyFillCount"] == len(buys)
    # Zero fee/slippage and protective fills at 100 return capital to start.
    assert d(summary["endingCapital"]) == Decimal("1000")
