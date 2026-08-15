"""Unit tests for Feature 011 final-result freeze / backfill."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SimulationSessionRow
from app.simulation.final_result import (
    SOURCE_BACKFILL,
    SOURCE_STOP,
    build_final_result,
    ensure_final_result_backfill,
    parse_final_result,
    persist_final_result,
)


def _row(**over) -> SimulationSessionRow:
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        mode="simulation",
        state="STOPPED",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="1000",
        max_position_size="1000",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.007",
        target_net_profit_amount="10",
        max_session_loss_amount="7",
        max_trades=20,
        duration_seconds=3600,
        fee_rate="0.002",
        slippage_rate="0.0005",
        strategy_id="dual_ema",
        strategy_params="{}",
        cash="1005",
        position_side="flat",
        position_qty="0",
        trade_count=2,
        strategy_fill_count=2,
        cumulative_fees="1",
        cumulative_slippage_cost="0.5",
        cumulative_gross_realized="6.5",
        position_flatten_status="flat",
        stop_reason="manual",
        stopped_at=now,
        created_at=now,
        updated_at=now,
    )
    base.update(over)
    return SimulationSessionRow(**base)


def test_flat_stop_is_complete():
    row = _row()
    fr = build_final_result(row, source=SOURCE_STOP)
    assert fr["complete"] is True
    assert fr["endingEquity"] == "1005"
    assert fr["netPnl"] == "5"
    assert fr["returnPct"] is not None
    assert fr["source"] == "stop"


def test_long_without_mark_is_incomplete():
    row = _row(position_side="long", position_qty="0.01", cash="100", position_flatten_status="unsafe_unflattened")
    fr = build_final_result(row, source=SOURCE_STOP, mark_price=None, mark_safe=False)
    assert fr["complete"] is False
    assert fr["endingEquity"] is None
    assert fr["netPnl"] is None
    assert fr["returnPct"] is None


def test_long_with_safe_mark_is_complete():
    row = _row(position_side="long", position_qty="0.01", cash="100")
    fr = build_final_result(
        row,
        source=SOURCE_STOP,
        mark_price=Decimal("65000"),
        mark_safe=True,
    )
    assert fr["complete"] is True
    assert fr["endingEquity"] is not None
    assert fr["netPnl"] is not None
    assert fr["markPrice"] == "65000"


def test_backfill_never_fetches_market(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fr.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = TestingSession()
    row = _row(final_result_json=None)
    db.add(row)
    db.commit()

    with patch("app.simulation.final_result.get_market_data_service", create=True) as mock_mds:
        # ensure helper does not import/call market data; assert via no AttributeError path
        fr = ensure_final_result_backfill(db, row)
        mock_mds.assert_not_called()

    assert fr is not None
    assert fr["source"] == "backfill"
    assert fr["complete"] is True
    assert fr["markPrice"] is None

    # idempotent — second call does not rewrite
    first_json = row.final_result_json
    again = ensure_final_result_backfill(db, row)
    assert row.final_result_json == first_json
    assert again["netPnl"] == fr["netPnl"]
    db.close()


def test_backfill_long_is_incomplete_without_market(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fr2.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = TestingSession()
    row = _row(
        final_result_json=None,
        position_side="long",
        position_qty="0.01",
        cash="100",
        position_flatten_status="unsafe_unflattened",
    )
    db.add(row)
    db.commit()
    fr = ensure_final_result_backfill(db, row)
    assert fr["complete"] is False
    assert fr["endingEquity"] is None
    db.close()


def test_persist_does_not_overwrite_existing_with_later_marks(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fr3.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = TestingSession()
    row = _row(final_result_json=None, cash="1000")
    db.add(row)
    db.commit()
    first = persist_final_result(db, row, source=SOURCE_STOP)
    db.commit()
    row.cash = "9999"
    second = persist_final_result(
        db,
        row,
        source=SOURCE_STOP,
        mark_price=Decimal("1"),
        mark_safe=True,
    )
    assert second["cash"] == first["cash"]
    assert second["netPnl"] == first["netPnl"]
    assert parse_final_result(row.final_result_json)["cash"] == "1000"
    db.close()
