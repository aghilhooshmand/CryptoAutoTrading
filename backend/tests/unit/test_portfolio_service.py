"""Unit tests for Feature 009 portfolio identity, holdings, and service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PortfolioAllocationRow, PortfolioRow, SimulationSessionRow, TradeJournalRow
from app.portfolio import identity
from app.portfolio import repository as repo
from app.portfolio import service as svc
from app.portfolio.valuation import QuoteView
from app.simulation.clock import SystemClock
from app.simulation.session_service import _apply_fill


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()


def _seed_portfolio(db, cash: str = "1000") -> None:
    db.add(
        PortfolioRow(
            id=1,
            cash=cash,
            deployed="0",
            realized_pnl="0",
            unrealized_pnl="0",
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def _buy_btc(db, *, qty="0.005", price="80000", cash_delta="-400", quotes=None):
    return svc.apply_simulation_fill(
        db,
        asset="btc",
        side="BUY",
        qty=qty,
        cash_delta=cash_delta,
        fill_price=price,
        quotes=quotes,
    )


def test_available_equals_cash_minus_reserved():
    cash = Decimal("1000")
    reserved = Decimal("400")
    assert identity.available_from(cash, reserved) == Decimal("600")
    assert identity.assert_invariants(cash, reserved) == Decimal("600")


def test_quote_cash_from_usdt_quantity():
    assert identity.quote_cash_from_usdt_quantity(None) == Decimal("0")
    assert identity.quote_cash_from_usdt_quantity("500") == Decimal("500")


def test_equity_complete_and_sum_values():
    assert identity.equity_complete([]) is True
    assert identity.equity_complete(["btc"]) is False
    assert identity.sum_market_values([Decimal("500"), Decimal("450")]) == Decimal("950")


def test_reserved_cannot_exceed_cash():
    with pytest.raises(identity.CapitalIdentityError):
        identity.assert_invariants(Decimal("100"), Decimal("150"))


def test_sum_reserved():
    assert identity.sum_reserved(["100", "250.5", "0.5"]) == Decimal("351")


def test_total_pnl_and_return_helpers():
    assert identity.total_pnl(Decimal("0"), Decimal("50")) == Decimal("50")
    assert identity.total_pnl(Decimal("10"), None) is None
    assert identity.total_return(Decimal("50"), Decimal("900")) == Decimal("50") / Decimal("900")
    assert identity.total_return(Decimal("50"), Decimal("0")) is None
    assert identity.total_return(None, Decimal("900")) is None


def test_migrates_cash_column_to_usdt_holding(db):
    _seed_portfolio(db, "1000")
    snap = svc.build_snapshot(db)
    usdt = [h for h in snap["holdings"] if h["asset"] == "usdt"]
    assert len(usdt) == 1
    assert usdt[0]["quantity"] == "1000"
    assert usdt[0]["provenance"] == "simulation"
    assert usdt[0]["unrealizedPnl"] is None
    assert usdt[0]["return"] is None
    assert snap["cash"] == "1000"
    assert snap["equity"] == "1000"
    assert snap["equityComplete"] is True
    assert snap["bookProvenance"] == "simulation"
    assert snap["mode"] == "simulation"


def test_fail_closed_corrupt_cash_does_not_invent(db):
    db.add(
        PortfolioRow(
            id=1,
            cash="not-a-number",
            deployed="0",
            realized_pnl="0",
            unrealized_pnl="0",
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    snap = svc.build_snapshot(db)
    assert snap["warning"] is not None
    assert snap["cash"] == "0"
    assert snap["deployed"] == "0"
    assert snap["positions"] == []


def test_fail_closed_corrupt_allocation_does_not_invent_available(db):
    now = datetime.now(timezone.utc)
    _seed_portfolio(db, "1000")
    db.add(
        PortfolioAllocationRow(
            id="11111111-1111-1111-1111-111111111111",
            portfolio_id=1,
            label="ok",
            reserved_size="200",
            target_ref=None,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        PortfolioAllocationRow(
            id="22222222-2222-2222-2222-222222222222",
            portfolio_id=1,
            label="bad",
            reserved_size="not-a-number",
            target_ref=None,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    snap = svc.build_snapshot(db)
    assert snap["warning"] is not None
    assert "corrupt" in snap["warning"].lower()
    assert snap["available"] == "0"
    assert snap["reserved"] == "0"
    assert snap["cash"] == "1000"
    assert len(snap["allocations"]) == 2


def test_corrupt_allocation_mutations_return_portfolio_error(db):
    now = datetime.now(timezone.utc)
    _seed_portfolio(db, "1000")
    db.add(
        PortfolioAllocationRow(
            id="11111111-1111-1111-1111-111111111111",
            portfolio_id=1,
            label="bad",
            reserved_size="not-a-number",
            target_ref=None,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    with pytest.raises(svc.PortfolioError) as fund_exc:
        svc.set_funding(db, "1000")
    assert fund_exc.value.code == "invalid_config"
    assert fund_exc.value.http_status == 400

    with pytest.raises(svc.PortfolioError) as create_exc:
        svc.create_allocation(db, label="x", reserved_size="10", target_ref=None)
    assert create_exc.value.code == "invalid_config"

    again = svc.build_snapshot(db)
    assert again["cash"] == "1000"
    assert len(again["allocations"]) == 1


def test_service_mutations_do_not_call_trading(db):
    with (
        patch("app.simulation.worker.ensure_worker_running") as w,
        patch("app.api.simulation.router") as sim,
        patch("app.api.backtest.router") as bt,
    ):
        svc.set_funding(db, "1000")
        svc.create_allocation(db, label="A", reserved_size="250", target_ref="rsi")
        snap = svc.build_snapshot(db)
        assert snap["cash"] == "1000"
        assert snap["reserved"] == "250"
        assert snap["available"] == "750"
        w.assert_not_called()
        assert sim.start_session.call_count == 0 if hasattr(sim, "start_session") else True
        assert bt.create_run.call_count == 0 if hasattr(bt, "create_run") else True


def test_create_over_reserve_rejected(db):
    svc.set_funding(db, "100")
    with pytest.raises(svc.PortfolioError) as exc:
        svc.create_allocation(db, label="Too big", reserved_size="150", target_ref=None)
    assert exc.value.code == "invalid_config"
    snap = svc.build_snapshot(db)
    assert snap["reserved"] == "0"
    assert snap["cash"] == "100"


def test_buy_then_sell_updates_usdt_btc_cost_and_realized(db):
    quotes = {"btc": QuoteView(price=Decimal("90000"), status="fresh")}
    svc.set_funding(db, "1000")
    bought = _buy_btc(db, quotes=quotes)
    assert bought is not None
    assert bought["cash"] == "600"
    btc = next(h for h in bought["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.005"
    assert btc["averageCost"] == "80000"
    assert btc["provenance"] == "simulation"
    usdt = next(h for h in bought["holdings"] if h["asset"] == "usdt")
    assert usdt["unrealizedPnl"] is None
    assert usdt["return"] is None

    sold = svc.apply_simulation_fill(
        db,
        asset="btc",
        side="SELL",
        qty="0.005",
        cash_delta="450",
        fill_price="90000",
        quotes=quotes,
    )
    assert sold is not None
    assert sold["cash"] == "1050"
    assert [h["asset"] for h in sold["holdings"]] == ["usdt"]
    usdt = next(h for h in sold["holdings"] if h["asset"] == "usdt")
    assert usdt["realizedPnl"] == "50"


def test_insufficient_usdt_refuses_without_snapshot_or_negative_cash(db):
    svc.set_funding(db, "100")
    n = repo.count_snapshots(db)
    refused = _buy_btc(db, cash_delta="-400")
    assert refused is None
    snap = svc.build_snapshot(db)
    assert snap["cash"] == "100"
    assert snap["warning"] == svc.FILL_APPLY_INSUFFICIENT
    assert [h["asset"] for h in snap["holdings"]] == ["usdt"]
    assert repo.count_snapshots(db) == n


def test_corrupt_warning_precedes_fill_apply_warning(db):
    """Corrupt-state GET warning beats a persisted fill-apply warning (C1)."""
    svc.set_funding(db, "100")
    refused = _buy_btc(db, cash_delta="-400")
    assert refused is None
    snap = svc.build_snapshot(db)
    assert snap["warning"] == svc.FILL_APPLY_INSUFFICIENT
    portfolio = repo.get_portfolio(db)
    assert portfolio is not None
    assert portfolio.fill_apply_warning == svc.FILL_APPLY_INSUFFICIENT

    now = datetime.now(timezone.utc)
    db.add(
        PortfolioAllocationRow(
            id="11111111-1111-1111-1111-111111111111",
            portfolio_id=1,
            label="bad",
            reserved_size="not-a-number",
            target_ref=None,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    snap2 = svc.build_snapshot(db)
    assert snap2["warning"] == svc.CORRUPT_ALLOCATION_MSG
    assert "corrupt" in snap2["warning"].lower()
    assert snap2["warning"] != svc.FILL_APPLY_INSUFFICIENT
    # Fill-apply text remains stored until a successful apply; it is not shown.
    portfolio2 = repo.get_portfolio(db)
    assert portfolio2 is not None
    assert portfolio2.fill_apply_warning == svc.FILL_APPLY_INSUFFICIENT
    assert snap2["cash"] == "100"
    assert snap2["available"] == "0"
    assert snap2["reserved"] == "0"


def test_partial_valuation_excludes_unvalued_from_equity(db):
    svc.set_funding(db, "1000")
    _buy_btc(db)
    snap = svc.build_snapshot(db, quotes={"btc": QuoteView(price=None, status="unavailable")})
    assert snap["cash"] == "600"
    assert snap["equity"] == "600"
    assert snap["equityComplete"] is False
    assert snap["unvaluedAssets"] == ["btc"]
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.005"
    assert btc["price"] is None
    assert btc["marketValue"] is None
    assert btc["unrealizedPnl"] is None
    assert btc["return"] is None
    assert btc["priceStatus"] == "unavailable"


def test_stale_quote_included_in_equity(db):
    svc.set_funding(db, "1000")
    _buy_btc(db)
    snap = svc.build_snapshot(
        db,
        quotes={"btc": QuoteView(price=Decimal("90000"), status="stale")},
    )
    assert snap["equity"] == "1050"
    assert snap["equityComplete"] is True
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["priceStatus"] == "stale"
    assert btc["marketValue"] == "450"
    assert btc["unrealizedPnl"] == "50"
    assert btc["return"] == "0.125"
    assert btc["weight"] is not None


def test_unknown_cost_nulls_pnl_and_return(db):
    svc.set_funding(db, "1000")
    repo.upsert_holding(
        db,
        asset="btc",
        quantity="0.005",
        average_cost=None,
        provenance="simulation",
    )
    db.commit()
    snap = svc.build_snapshot(
        db,
        quotes={"btc": QuoteView(price=Decimal("90000"), status="fresh")},
    )
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["averageCost"] is None
    assert btc["marketValue"] == "450"
    assert btc["unrealizedPnl"] is None
    assert btc["return"] is None
    assert snap["totalPnl"] is None
    assert snap["totalReturn"] is None


def test_total_pnl_and_return_when_cost_basis_known(db):
    svc.set_funding(db, "1000")
    _buy_btc(db)
    snap = svc.build_snapshot(
        db,
        quotes={"btc": QuoteView(price=Decimal("90000"), status="fresh")},
    )
    assert snap["realizedPnl"] == "0"
    assert snap["unrealizedPnl"] == "50"
    assert snap["totalPnl"] == "50"
    assert snap["totalReturn"] == identity.money_str(Decimal("50") / Decimal("1000"))


def test_usdt_only_total_pnl_and_return_are_zero(db):
    svc.set_funding(db, "1000")
    snap = svc.build_snapshot(db)
    usdt = next(h for h in snap["holdings"] if h["asset"] == "usdt")
    assert usdt["unrealizedPnl"] is None
    assert usdt["return"] is None
    assert snap["totalPnl"] == "0"
    assert snap["totalReturn"] == "0"


def test_unvalued_holding_omits_total_pnl_and_return(db):
    svc.set_funding(db, "1000")
    _buy_btc(db)
    snap = svc.build_snapshot(db, quotes={"btc": QuoteView(price=None, status="unavailable")})
    assert snap["totalPnl"] is None
    assert snap["totalReturn"] is None


def test_get_does_not_append_snapshot(db):
    svc.set_funding(db, "100")
    n = repo.count_snapshots(db)
    svc.build_snapshot(db)
    svc.build_snapshot(db)
    assert repo.count_snapshots(db) == n


def test_mutations_append_one_snapshot_each(db):
    assert repo.count_snapshots(db) == 0
    svc.set_funding(db, "1000")
    _buy_btc(db)
    svc.create_allocation(db, label="A", reserved_size="250", target_ref="rsi")
    assert repo.count_snapshots(db) == 3
    assert repo.list_snapshot_reasons(db) == ["funding", "simulation_fill", "allocation_create"]


def test_allocation_does_not_change_btc_quantity(db):
    svc.set_funding(db, "1000")
    _buy_btc(db)
    svc.create_allocation(db, label="A", reserved_size="250", target_ref=None)
    snap = svc.build_snapshot(db)
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.005"
    assert snap["reserved"] == "250"
    assert snap["cash"] == "600"
    assert snap["available"] == "350"


def test_deployed_and_positions_from_active_long_session(db):
    svc.set_funding(db, "1000")
    now = datetime.now(timezone.utc)
    db.add(
        SimulationSessionRow(
            id="44444444-4444-4444-4444-444444444444",
            mode="simulation",
            state="RUNNING",
            symbol="btc_usdt",
            timeframe="1h",
            starting_capital="1000",
            allocated_capital="1000",
            max_position_size="500",
            target_net_profit_rate="0.01",
            max_session_loss_rate="0.007",
            target_net_profit_amount="5",
            max_session_loss_amount="3.5",
            max_trades=20,
            duration_seconds=3600,
            fee_rate="0.001",
            slippage_rate="0.0005",
            strategy_id="dual_ema",
            cash="800",
            position_side="long",
            position_qty="0.005",
            cost_basis="200",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    snap = svc.build_snapshot(db)
    assert snap["deployed"] == "200"
    assert len(snap["positions"]) == 1
    pos = snap["positions"][0]
    assert pos["sessionId"] == "44444444-4444-4444-4444-444444444444"
    assert pos["asset"] == "btc"
    assert pos["symbol"] == "btc_usdt"
    assert pos["side"] == "long"
    assert pos["quantity"] == "0.005"
    assert pos["costBasis"] == "200"


def test_no_active_long_means_zero_deployed(db):
    svc.set_funding(db, "1000")
    snap = svc.build_snapshot(db)
    assert snap["deployed"] == "0"
    assert snap["positions"] == []


def test_apply_fill_hook_writes_portfolio_and_keeps_journal(db):
    svc.set_funding(db, "1000")
    now = datetime.now(timezone.utc)
    session_id = str(uuid4())
    row = SimulationSessionRow(
        id=session_id,
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="1000",
        max_position_size="500",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.007",
        target_net_profit_amount="5",
        max_session_loss_amount="3.5",
        max_trades=20,
        duration_seconds=3600,
        fee_rate="0",
        slippage_rate="0",
        strategy_id="dual_ema",
        cash="1000",
        position_side="flat",
        position_qty="0",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    fill = SimpleNamespace(
        cash_delta=Decimal("-200"),
        fee=Decimal("0"),
        slippage_cost=Decimal("0"),
        reference_price=Decimal("80000"),
        fill_price=Decimal("80000"),
        notional=Decimal("200"),
    )
    trade = _apply_fill(
        row,
        side="BUY",
        qty=Decimal("0.0025"),
        fill=fill,
        is_forced=False,
        candle_open_time=None,
        clock=SystemClock(),
        db=db,
    )
    db.commit()
    assert trade.session_id == session_id
    journals = db.query(TradeJournalRow).filter(TradeJournalRow.session_id == session_id).all()
    assert len(journals) == 1
    snap = svc.build_snapshot(db)
    assert snap["cash"] == "800"
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.0025"
    assert snap["warning"] is None


def test_apply_fill_hook_refuses_portfolio_keeps_journal(db):
    svc.set_funding(db, "50")
    now = datetime.now(timezone.utc)
    session_id = str(uuid4())
    row = SimulationSessionRow(
        id=session_id,
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="1000",
        max_position_size="500",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.007",
        target_net_profit_amount="5",
        max_session_loss_amount="3.5",
        max_trades=20,
        duration_seconds=3600,
        fee_rate="0",
        slippage_rate="0",
        strategy_id="dual_ema",
        cash="1000",
        position_side="flat",
        position_qty="0",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    fill = SimpleNamespace(
        cash_delta=Decimal("-200"),
        fee=Decimal("0"),
        slippage_cost=Decimal("0"),
        reference_price=Decimal("80000"),
        fill_price=Decimal("80000"),
        notional=Decimal("200"),
    )
    _apply_fill(
        row,
        side="BUY",
        qty=Decimal("0.0025"),
        fill=fill,
        is_forced=False,
        candle_open_time=None,
        clock=SystemClock(),
        db=db,
    )
    db.commit()
    journals = db.query(TradeJournalRow).filter(TradeJournalRow.session_id == session_id).all()
    assert len(journals) == 1
    snap = svc.build_snapshot(db)
    assert snap["cash"] == "50"
    assert snap["warning"] == svc.FILL_APPLY_INSUFFICIENT
    assert [h["asset"] for h in snap["holdings"]] == ["usdt"]
    assert row.cash == "800"
