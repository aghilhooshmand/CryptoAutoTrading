"""Protective exit precedence and cycle accounting (Feature 025 US2)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DecisionJournalRow, TradeJournalRow
from app.execution.tpsl import REASON_STOP_LOSS, REASON_TAKE_PROFIT, derive_levels, evaluate_triggers
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.money import as_str, d
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import create_session
from app.strategy.base import CandleClose, SignalSide, StrategySignal


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = TestingSession()
    from app.portfolio import service as portfolio_svc

    portfolio_svc.set_funding(s, "100000")
    try:
        yield s
    finally:
        s.close()


def _body(**overrides):
    body = {
        "mode": "simulation",
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "startingCapital": "1000",
        "allocatedCapital": "1000",
        "maxPositionSize": "1000",
        "targetNetProfitRate": "10",
        "maxSessionLossRate": "0.99",
        "maxTrades": 20,
        "durationSeconds": 86400,
        "strategyId": "dual_ema",
        "takeProfitPercent": "0.02",
        "stopLossPercent": "0.01",
    }
    body.update(overrides)
    return body


def _market(now: datetime, *, candles: list[Candlestick], mark: str = "100"):
    series = CandlestickSeries(
        symbol="btc_usdt",
        interval="1h",
        candles=candles,
        source="XT",
        retrievedAt=now,
    )
    quote = MarketQuote(
        symbol="btc_usdt",
        lastPrice=mark,
        source="XT",
        observedAt=now,
        retrievedAt=now,
        status=MarketStatus.FRESH,
    )
    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=quote)
    mock.get_candles = AsyncMock(return_value=series)
    return mock


def _run_tick(db, row, mock, now):
    clock = FakeClock(now)

    async def _run():
        with patch("app.simulation.pipeline.get_market_data_service", return_value=mock):
            await process_session_tick(db, row, clock)

    asyncio.run(_run())


def _seed_long(row, *, entry_fill: str, entry_candle: int, mark_ref: str = "100"):
    tp_pct = d(row.take_profit_percent) if row.take_profit_percent else None
    sl_pct = d(row.stop_loss_percent) if row.stop_loss_percent else None
    tp, sl = derive_levels(d(entry_fill), tp_pct, sl_pct)
    row.state = "RUNNING"
    row.position_side = "long"
    row.position_qty = "1"
    row.cash = as_str(d(row.starting_capital) - d(entry_fill))
    row.entry_ref_price = mark_ref
    row.entry_fill_price = entry_fill
    row.entry_fee = "0"
    row.entry_slippage_cost = "0"
    row.cost_basis = entry_fill
    row.entry_fill_candle_open_time = entry_candle
    row.take_profit_price = as_str(tp) if tp is not None else None
    row.stop_loss_price = as_str(sl) if sl is not None else None
    row.last_processed_candle_open_time = entry_candle
    row.strategy_fill_count = 1
    row.trade_count = 1


class _AlwaysSellStrategy:
    def min_history_candles(self) -> int:
        return 1

    def evaluate(self, closes):
        last = closes[-1]
        return StrategySignal(
            side=SignalSide.SELL,
            candle_open_time=last.open_time,
            fast_ema=None,
            slow_ema=None,
        )


def test_evaluate_triggers_sl_wins_same_candle():
    reason = evaluate_triggers(
        candle_open_time=2000,
        high=Decimal("103"),
        low=Decimal("98"),
        entry_fill_candle_open_time=1000,
        tp_price=Decimal("102"),
        sl_price=Decimal("99"),
    )
    assert reason == REASON_STOP_LOSS


def test_sl_beats_strategy_sell_same_candle(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="103", low="98", close="99"),
    ]
    mock = _market(now, candles=candles, mark="99")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysSellStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "flat"
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_STOP_LOSS)
        .count()
        == 1
    )
    assert (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL", is_forced_close=True)
        .count()
        == 1
    )
    assert row.strategy_fill_count == 1


def test_tp_beats_strategy_when_sl_not_hit(db):
    row = create_session(db, _body(stopLossPercent=None))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="103", low="100", close="102"),
    ]
    mock = _market(now, candles=candles, mark="102")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysSellStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "flat"
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_TAKE_PROFIT)
        .count()
        == 1
    )
    assert row.strategy_fill_count == 1


def test_strategy_sell_when_levels_not_hit(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="100.5", low="99.5", close="100"),
    ]
    mock = _market(now, candles=candles, mark="100")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysSellStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "flat"
    sell = (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL")
        .one()
    )
    assert sell.is_forced_close is False
    assert row.strategy_fill_count == 2


def test_repeated_cycles_protective_does_not_consume_max_trades(db):
    """Three strategy BUYs + three protective SELLs → strategyFillCount == 3.

    Simulation advances one newest closed candle per tick, so we feed the series
    progressively (same as live poll behavior).
    """
    row = create_session(
        db,
        _body(maxTrades=10, stopLossPercent=None, feeRate="0", slippageRate="0"),
    )
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    base = int(now.timestamp() * 1000) - 10 * 3600 * 1000

    class _CycleStrategy:
        def min_history_candles(self) -> int:
            return 1

        def evaluate(self, closes):
            last = closes[-1]
            if row.position_side == "flat":
                return StrategySignal(SignalSide.BUY, last.open_time, None, None)
            return StrategySignal(SignalSide.HOLD, last.open_time, None, None, "hold")

    candles: list[Candlestick] = []
    for cycle in range(3):
        buy_ot = base + cycle * 2 * 3600_000
        tp_ot = buy_ot + 3600_000
        candles.append(Candlestick(openTime=buy_ot, open="100", high="100", low="100", close="100"))
        candles.append(Candlestick(openTime=tp_ot, open="100", high="103", low="100", close="102"))

    row.state = "RUNNING"
    row.last_processed_candle_open_time = base - 3600_000
    db.commit()
    strat = _CycleStrategy()
    with patch("app.simulation.pipeline.build_from_stored", return_value=strat):
        for i in range(len(candles)):
            mock = _market(now, candles=candles[: i + 1], mark="100")
            _run_tick(db, row, mock, now)
            db.refresh(row)

    assert row.strategy_fill_count == 3
    protective_sells = (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL", is_forced_close=True)
        .count()
    )
    assert protective_sells == 3
    assert row.position_side == "flat"
    assert d(row.position_qty) == Decimal("0")

    trades = (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id)
        .order_by(TradeJournalRow.created_at.asc())
        .all()
    )
    assert len(trades) == 6  # 3 BUY + 3 protective SELL
    sum_deltas = sum((d(t.cash_delta) for t in trades), Decimal("0"))
    sum_fees = sum((d(t.fee) for t in trades), Decimal("0"))
    sum_slip = sum((d(t.slippage_cost) for t in trades), Decimal("0"))
    assert d(row.cash) == d(row.starting_capital) + sum_deltas
    assert d(row.cumulative_fees) == sum_fees
    assert d(row.cumulative_slippage_cost) == sum_slip
    # Zero-cost round-trips at mark 100 return cash to starting
    assert d(row.cash) == d(row.starting_capital)


def test_session_profit_target_beats_take_profit(db):
    """FR-006: session hard-stop runs before protective TP on the same tick."""
    row = create_session(
        db,
        _body(
            takeProfitPercent="0.02",
            stopLossPercent=None,
            targetNetProfitRate="0.05",
            feeRate="0",
            slippageRate="0",
        ),
    )
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    # Mark high enough that liquidation equity hits profit target before TP path
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="200", low="100", close="180"),
    ]
    mock = _market(now, candles=candles, mark="180")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysSellStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "profit_target"
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_TAKE_PROFIT)
        .count()
        == 0
    )


def test_session_max_loss_beats_stop_loss(db):
    """FR-006: session max-loss hard-stop before protective SL."""
    row = create_session(
        db,
        _body(
            takeProfitPercent=None,
            stopLossPercent="0.50",
            maxSessionLossRate="0.05",
            feeRate="0",
            slippageRate="0",
        ),
    )
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="100", low="40", close="50"),
    ]
    mock = _market(now, candles=candles, mark="50")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_AlwaysSellStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.stop_reason == "max_loss"
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_STOP_LOSS)
        .count()
        == 0
    )
