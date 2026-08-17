"""Real automatic protective/reducing exits skip confirmation (Feature 015 US2)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DecisionJournalRow, PendingEntryConfirmationRow, TradeJournalRow
from app.execution.real import set_client_factory_override
from app.execution.tpsl import REASON_STOP_LOSS, REASON_TAKE_PROFIT
from app.market_data.models import Candlestick, CandlestickSeries, MarketQuote, MarketStatus
from app.portfolio.repository import list_holdings
from app.simulation.clock import FakeClock
from app.simulation.money import as_str, d
from app.simulation.pipeline import process_session_tick
from app.simulation.real_gates import set_try_free_usdt_override
from app.simulation.session_service import create_session, stop_session_async
from app.strategy.base import SignalSide, StrategySignal


class FillingXtClient:
    def __init__(self) -> None:
        self.place_calls: list[dict] = []

    async def place_market_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return {"orderId": f"xt-{len(self.place_calls)}"}

    async def get_order(self, order_id: str):
        last = self.place_calls[-1]
        qty = last.get("quantity") or "0.001"
        return {
            "orderId": order_id,
            "symbol": last.get("symbol", "btc_usdt"),
            "side": last.get("side", "SELL"),
            "status": "FILLED",
            "executedQty": qty,
            "price": "100",
        }

    async def aclose(self) -> None:
        return None


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
            reason_code="test_sell",
        )


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/e.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    set_try_free_usdt_override(lambda: Decimal("100"))
    s = TestingSession()
    from app.portfolio import service as portfolio_svc

    portfolio_svc.set_funding(s, "100000")
    fake = FillingXtClient()
    set_client_factory_override(lambda _c: fake)
    s._xt = fake  # type: ignore[attr-defined]
    try:
        yield s
    finally:
        s.close()
        set_try_free_usdt_override(None)
        set_client_factory_override(None)


def _real_body(**overrides):
    body = {
        "mode": "real",
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "allocatedCapital": "25",
        "maxPositionSize": "25",
        "targetNetProfitRate": "10",
        "maxSessionLossRate": "0.99",
        "maxTrades": 20,
        "durationSeconds": 86400,
        "strategyId": "dual_ema",
        "takeProfitPercent": "0.02",
        "stopLossPercent": "0.01",
        "feeRate": "0",
        "slippageRate": "0",
    }
    body.update(overrides)
    return body


def _holdings(db):
    return {(h.asset, h.quantity) for h in list_holdings(db)}


def _pending_count(db, session_id: str) -> int:
    return (
        db.query(PendingEntryConfirmationRow)
        .filter(PendingEntryConfirmationRow.session_id == session_id)
        .count()
    )


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


def _seed_long(row, *, entry_fill: str, entry_candle: int, qty: str = "0.001"):
    from app.execution.tpsl import derive_levels

    tp_pct = d(row.take_profit_percent) if row.take_profit_percent else None
    sl_pct = d(row.stop_loss_percent) if row.stop_loss_percent else None
    tp, sl = derive_levels(d(entry_fill), tp_pct, sl_pct)
    row.state = "RUNNING"
    row.started_at = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row.position_side = "long"
    row.position_qty = qty
    row.cash = as_str(d(row.starting_capital) - d(entry_fill) * d(qty))
    row.entry_ref_price = entry_fill
    row.entry_fill_price = entry_fill
    row.entry_fee = "0"
    row.entry_slippage_cost = "0"
    row.cost_basis = as_str(d(entry_fill) * d(qty))
    row.entry_fill_candle_open_time = entry_candle
    row.take_profit_price = as_str(tp) if tp is not None else None
    row.stop_loss_price = as_str(sl) if sl is not None else None
    row.last_processed_candle_open_time = entry_candle
    row.strategy_fill_count = 1
    row.trade_count = 1


def test_protective_sl_skips_confirm_and_places_xt_sell(db):
    before = _holdings(db)
    row = create_session(db, _real_body())
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
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
    assert _pending_count(db, row.id) == 0
    assert db._xt.place_calls[0]["side"] == "SELL"
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
    assert _holdings(db) == before


def test_protective_tp_skips_confirm(db):
    row = create_session(db, _real_body(stopLossPercent=None))
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
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
    assert _pending_count(db, row.id) == 0
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_TAKE_PROFIT)
        .count()
        == 1
    )


def test_reducing_strategy_sell_skips_confirm(db):
    before = _holdings(db)
    row = create_session(db, _real_body())
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
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
    assert _pending_count(db, row.id) == 0
    sell = db.query(TradeJournalRow).filter_by(session_id=row.id, side="SELL").one()
    assert sell.is_forced_close is False
    assert db._xt.place_calls[0]["side"] == "SELL"
    assert _holdings(db) == before


def test_stop_flatten_skips_confirm_and_places_xt_sell(db):
    before = _holdings(db)
    row = create_session(db, _real_body())
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    entry_ot = int(now.timestamp() * 1000) - 3 * 3600 * 1000
    _seed_long(row, entry_fill="100", entry_candle=entry_ot)
    db.commit()
    mock = _market(now, candles=[], mark="100")

    async def _stop():
        with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
            await stop_session_async(db, row.id, "emergency", clock=FakeClock(now))

    asyncio.run(_stop())
    db.refresh(row)
    assert row.state == "STOPPED"
    assert row.position_side == "flat"
    assert _pending_count(db, row.id) == 0
    assert db._xt.place_calls[0]["side"] == "SELL"
    assert (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL", is_forced_close=True)
        .count()
        == 1
    )
    assert _holdings(db) == before


def test_sl_beats_strategy_sell_same_candle(db):
    row = create_session(db, _real_body())
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
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
    assert (
        db.query(DecisionJournalRow)
        .filter_by(session_id=row.id, reason_code=REASON_STOP_LOSS)
        .count()
        == 1
    )
    assert (
        db.query(TradeJournalRow)
        .filter_by(session_id=row.id, side="SELL", is_forced_close=False)
        .count()
        == 0
    )
    assert row.strategy_fill_count == 1
