"""Simulation protective TP/SL exits (Feature 025 US1)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DecisionJournalRow, TradeJournalRow
from app.execution.tpsl import REASON_STOP_LOSS, REASON_TAKE_PROFIT, derive_levels
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.simulation.clock import FakeClock
from app.simulation.money import as_str, d
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import create_session


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
        # Wide bands so protective-exit fixtures are not tripped by session hard-stops
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
    # Preserve ~flat equity vs starting capital so hard-stops do not fire first
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


class _HoldStrategy:
    def min_history_candles(self) -> int:
        return 1

    def evaluate(self, closes):
        from app.strategy.base import SignalSide, StrategySignal

        last = closes[-1]
        return StrategySignal(
            side=SignalSide.HOLD,
            candle_open_time=last.open_time,
            fast_ema=None,
            slow_ema=None,
            reason_code="hold",
        )


def test_create_rejects_invalid_tpsl(db):
    from app.simulation.session_service import SessionError

    with pytest.raises(SessionError) as exc:
        create_session(db, _body(stopLossPercent="1"))
    assert exc.value.code == "invalid_config"


def test_create_and_status_expose_percents(db):
    row = create_session(db, _body())
    assert row.take_profit_percent == "0.02"
    assert row.stop_loss_percent == "0.01"
    assert row.take_profit_price is None


def test_entry_bar_skip_no_exit(db):
    row = create_session(db, _body())
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 2 * 3600 * 1000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot - 3600_000, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=entry_ot, open="100", high="200", low="1", close="100"),
    ]
    mock = _market(now, candles=candles, mark="100")
    row.last_processed_candle_open_time = entry_ot - 3600_000
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_HoldStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "long"
    forced = (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_TAKE_PROFIT)
        .all()
    )
    assert forced == []
    forced_sl = (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_STOP_LOSS)
        .all()
    )
    assert forced_sl == []


def test_take_profit_uses_mark_not_level(db):
    row = create_session(db, _body(stopLossPercent=None))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    tp_level = d(row.take_profit_price)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="103", low="100", close="102"),
    ]
    mark = "101.5"
    mock = _market(now, candles=candles, mark=mark)
    db.commit()
    _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "flat"
    trade = (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL", is_forced_close=True)
        .one()
    )
    assert d(trade.reference_price) == d(mark)
    assert d(trade.fill_price) != tp_level
    decision = (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_TAKE_PROFIT)
        .one()
    )
    assert decision.outcome == "forced"
    assert row.strategy_fill_count == 1  # protective did not increment


def test_stop_loss_forced_exit(db):
    row = create_session(db, _body(takeProfitPercent=None))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="100", low="98", close="99"),
    ]
    mock = _market(now, candles=candles, mark="99")
    db.commit()
    _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "flat"
    assert row.take_profit_price is None
    assert row.stop_loss_price is None
    assert row.entry_fill_candle_open_time is None
    decision = (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_STOP_LOSS)
        .one()
    )
    assert decision.outcome == "forced"


def test_disabled_tpsl_no_protective_path(db):
    row = create_session(db, _body(takeProfitPercent=None, stopLossPercent=None))
    now = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    row.started_at = now
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    trigger_ot = entry_ot + 3600_000
    row.state = "RUNNING"
    row.position_side = "long"
    row.position_qty = "1"
    row.cash = as_str(d(row.starting_capital) - d("100"))
    row.entry_fill_price = "100"
    row.entry_ref_price = "100"
    row.entry_fill_candle_open_time = entry_ot
    row.last_processed_candle_open_time = entry_ot
    candles = [
        Candlestick(openTime=entry_ot, open="100", high="100", low="100", close="100"),
        Candlestick(openTime=trigger_ot, open="100", high="200", low="1", close="100"),
    ]
    mock = _market(now, candles=candles, mark="100")
    db.commit()
    with patch("app.simulation.pipeline.build_from_stored", return_value=_HoldStrategy()):
        _run_tick(db, row, mock, now)
    db.refresh(row)
    assert row.position_side == "long"
    assert (
        db.query(DecisionJournalRow)
        .filter(DecisionJournalRow.session_id == row.id, DecisionJournalRow.reason_code.in_([REASON_TAKE_PROFIT, REASON_STOP_LOSS]))
        .count()
        == 0
    )
