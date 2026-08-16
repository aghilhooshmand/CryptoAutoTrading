"""Feature 014 reconciliation gate tests."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    DecisionJournalRow,
    PortfolioHoldingRow,
    PortfolioRow,
    SimulationSessionRow,
    TradeJournalRow,
)
from app.portfolio.repository import PORTFOLIO_ID
from app.simulation.reconcile import (
    GATE_MARK,
    GATE_PORTFOLIO,
    GATE_SESSION_JOURNAL,
    GATE_UNSAFE_UNFLATTENED,
    GATE_WATERMARK,
    reconcile_session,
)


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
        position_flatten_status="n/a",
        created_at=now,
        updated_at=now,
    )
    base.update(over)
    return SimulationSessionRow(**base)


def test_g1_pass_flat_no_trades():
    db = _db()
    row = _row()
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert result.passed
    assert result.failed_gates == []


def test_g1_fail_cash_mismatch():
    db = _db()
    row = _row(cash="999")
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert not result.passed
    assert GATE_SESSION_JOURNAL in result.failed_gates


def test_g1_pass_with_trade_replay():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(cash="500", position_side="long", position_qty="0.01")
    db.add(row)
    db.add(
        TradeJournalRow(
            id="22222222-2222-2222-2222-222222222222",
            session_id=row.id,
            created_at=now,
            symbol="btc_usdt",
            side="BUY",
            qty="0.01",
            reference_price="50000",
            fill_price="50000",
            fee="0",
            slippage_cost="0",
            notional="500",
            cash_delta="-500",
            is_forced_close=False,
            candle_open_time=1_700_000_000_000,
        )
    )
    row.last_processed_candle_open_time = 1_700_000_000_000
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_SESSION_JOURNAL not in result.failed_gates


def test_g2_fail_null_watermark_with_journal():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row()
    db.add(row)
    db.add(
        DecisionJournalRow(
            id="33333333-3333-3333-3333-333333333333",
            session_id=row.id,
            created_at=now,
            candle_open_time=1_700_000_000_000,
            signal="HOLD",
            outcome="hold",
        )
    )
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_WATERMARK in result.failed_gates


def test_g2_fail_watermark_behind_journal():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(last_processed_candle_open_time=100)
    db.add(row)
    db.add(
        TradeJournalRow(
            id="22222222-2222-2222-2222-222222222222",
            session_id=row.id,
            created_at=now,
            symbol="btc_usdt",
            side="BUY",
            qty="0.01",
            reference_price="50000",
            fill_price="50000",
            fee="0",
            slippage_cost="0",
            notional="500",
            cash_delta="-500",
            is_forced_close=False,
            candle_open_time=200,
        )
    )
    row.cash = "500"
    row.position_side = "long"
    row.position_qty = "0.01"
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_WATERMARK in result.failed_gates


def test_g3_unbound_long_fails():
    db = _db()
    row = _row(position_side="long", position_qty="1", cash="500", allocation_id=None)
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_PORTFOLIO in result.failed_gates


def test_g3_unbound_flat_with_leftover_base_holding_fails():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(
        allocation_id=None,
        cash="1000",
        position_side="flat",
        position_qty="0",
        symbol="btc_usdt",
    )
    db.add(row)
    db.add(
        PortfolioRow(
            id=PORTFOLIO_ID,
            cash="0",
            deployed="0",
            realized_pnl="0",
            unrealized_pnl="0",
            updated_at=now,
        )
    )
    db.add(
        PortfolioHoldingRow(
            id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            portfolio_id=PORTFOLIO_ID,
            asset="btc",
            quantity="0.01",
            average_cost="50000",
            realized_pnl="0",
            provenance="simulation",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_PORTFOLIO in result.failed_gates


def test_g3_unbound_flat_without_base_holding_passes():
    db = _db()
    row = _row(allocation_id=None, cash="1000", position_side="flat", position_qty="0")
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_PORTFOLIO not in result.failed_gates
    assert result.passed


def test_g3_bound_mismatch_fails():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(
        allocation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cash="1000",
        position_side="flat",
        position_qty="0",
    )
    db.add(row)
    db.add(PortfolioRow(id=PORTFOLIO_ID, cash="0", deployed="0", realized_pnl="0", unrealized_pnl="0", updated_at=now))
    db.add(
        PortfolioHoldingRow(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            portfolio_id=PORTFOLIO_ID,
            asset="usdt",
            quantity="50",
            average_cost=None,
            realized_pnl="0",
            provenance="simulation",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_PORTFOLIO in result.failed_gates


def test_g3_bound_agree_passes():
    db = _db()
    now = datetime.now(timezone.utc)
    row = _row(
        allocation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cash="1000",
        position_side="flat",
        position_qty="0",
    )
    db.add(row)
    db.add(PortfolioRow(id=PORTFOLIO_ID, cash="0", deployed="0", realized_pnl="0", unrealized_pnl="0", updated_at=now))
    db.add(
        PortfolioHoldingRow(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            portfolio_id=PORTFOLIO_ID,
            asset="usdt",
            quantity="1000",
            average_cost=None,
            realized_pnl="0",
            provenance="simulation",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_PORTFOLIO not in result.failed_gates
    assert result.passed


def test_g4_unsafe_unflattened():
    db = _db()
    row = _row(position_flatten_status="unsafe_unflattened")
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=True)
    assert GATE_UNSAFE_UNFLATTENED in result.failed_gates


def test_g5_long_needs_mark_safe():
    db = _db()
    row = _row(position_side="long", position_qty="1", cash="500")
    db.add(row)
    db.commit()
    result = reconcile_session(db, row, mark_safe=False)
    assert GATE_MARK in result.failed_gates
    # Also unbound long → portfolio fail
    assert GATE_PORTFOLIO in result.failed_gates
