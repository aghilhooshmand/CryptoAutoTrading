"""Feature 014 gap-skip unit tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow, SkippedGapAuditRow
from app.simulation.gap_skip import apply_offline_gap_skip
from app.simulation.reconcile import GATE_GAP


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _row(**over) -> SimulationSessionRow:
    now = datetime.now(timezone.utc)
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="1000",
        max_position_size="1000",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.01",
        target_net_profit_amount="10",
        max_session_loss_amount="10",
        max_trades=10,
        duration_seconds=3600,
        fee_rate="0.001",
        slippage_rate="0.0005",
        cash="1000",
        position_side="flat",
        position_qty="0",
        last_processed_candle_open_time=1_700_000_000_000,
        created_at=now,
        updated_at=now,
    )
    base.update(over)
    return SimulationSessionRow(**base)


def test_gap_skip_advances_and_audits():
    db = _db()
    row = _row()
    db.add(row)
    db.commit()
    prior = row.last_processed_candle_open_time
    newer = prior + 3_600_000
    ok, err = asyncio.run(
        apply_offline_gap_skip(db, row, market_candles_open_times=[prior, newer])
    )
    assert ok and err is None
    db.commit()
    db.refresh(row)
    assert row.last_processed_candle_open_time == newer
    audits = db.query(SkippedGapAuditRow).all()
    assert len(audits) == 1
    assert audits[0].from_open_time == prior
    assert audits[0].to_open_time == newer
    assert audits[0].reason == "offline_gap_skip"


def test_gap_skip_nothing_newer():
    db = _db()
    row = _row()
    db.add(row)
    db.commit()
    wm = row.last_processed_candle_open_time
    ok, err = asyncio.run(
        apply_offline_gap_skip(db, row, market_candles_open_times=[wm - 1000, wm])
    )
    assert ok and err is None
    assert row.last_processed_candle_open_time == wm
    assert db.query(SkippedGapAuditRow).count() == 0


def test_gap_skip_empty_when_no_watermark():
    db = _db()
    row = _row(last_processed_candle_open_time=None)
    db.add(row)
    db.commit()
    ok, err = asyncio.run(
        apply_offline_gap_skip(db, row, market_candles_open_times=[])
    )
    assert ok and err is None


def test_gap_skip_empty_with_watermark_fails_closed():
    db = _db()
    row = _row(last_processed_candle_open_time=1_700_000_000_000)
    db.add(row)
    db.commit()
    ok, err = asyncio.run(
        apply_offline_gap_skip(db, row, market_candles_open_times=[])
    )
    assert not ok
    assert err == GATE_GAP
    assert row.last_processed_candle_open_time == 1_700_000_000_000
    assert db.query(SkippedGapAuditRow).count() == 0


def test_gap_skip_unresolvable_on_fetch_fail():
    db = _db()
    row = _row()
    db.add(row)
    db.commit()

    from unittest.mock import AsyncMock, patch

    mock_svc = AsyncMock()
    mock_svc.get_candles = AsyncMock(side_effect=RuntimeError("down"))
    with patch("app.simulation.gap_skip.get_market_data_service", return_value=mock_svc):
        ok, err = asyncio.run(apply_offline_gap_skip(db, row, market_candles_open_times=None))
    assert not ok
    assert err == GATE_GAP
