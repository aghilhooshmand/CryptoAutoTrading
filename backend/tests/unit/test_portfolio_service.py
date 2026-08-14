"""Unit tests for Feature 009 portfolio identity, holdings, and service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PortfolioAllocationRow, PortfolioRow
from app.portfolio import identity
from app.portfolio import repository as repo
from app.portfolio import service as svc
from app.portfolio.valuation import QuoteView


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
    assert usdt[0]["provenance"] == "local_manual"
    assert snap["cash"] == "1000"
    assert snap["equity"] == "1000"
    assert snap["equityComplete"] is True


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


def test_partial_valuation_excludes_unvalued_from_equity(db):
    svc.set_funding(db, "500")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost="80000")
    snap = svc.build_snapshot(db, quotes={"btc": QuoteView(price=None, status="unavailable")})
    assert snap["cash"] == "500"
    assert snap["equity"] == "500"
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
    svc.set_funding(db, "500")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost="80000")
    snap = svc.build_snapshot(
        db,
        quotes={"btc": QuoteView(price=Decimal("90000"), status="stale")},
    )
    assert snap["equity"] == "950"
    assert snap["equityComplete"] is True
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["priceStatus"] == "stale"
    assert btc["marketValue"] == "450"
    assert btc["unrealizedPnl"] == "50"
    assert btc["return"] == "0.125"
    assert btc["weight"] is not None


def test_unknown_cost_nulls_pnl_and_return(db):
    svc.set_funding(db, "500")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost=None)
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
    svc.set_funding(db, "500")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost="80000")
    snap = svc.build_snapshot(
        db,
        quotes={"btc": QuoteView(price=Decimal("90000"), status="fresh")},
    )
    assert snap["realizedPnl"] == "0"
    assert snap["unrealizedPnl"] == "50"
    assert snap["totalPnl"] == "50"
    assert snap["totalReturn"] == identity.money_str(Decimal("50") / Decimal("900"))


def test_usdt_only_total_pnl_and_return_are_zero(db):
    svc.set_funding(db, "1000")
    snap = svc.build_snapshot(db)
    assert snap["totalPnl"] == "0"
    assert snap["totalReturn"] == "0"


def test_unvalued_holding_omits_total_pnl_and_return(db):
    svc.set_funding(db, "500")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost="80000")
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
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost="80000")
    svc.create_allocation(db, label="A", reserved_size="250", target_ref="rsi")
    assert repo.count_snapshots(db) == 3
    assert repo.list_snapshot_reasons(db) == ["funding", "holding_upsert", "allocation_create"]
    svc.delete_holding(db, "btc")
    assert repo.list_snapshot_reasons(db)[-1] == "holding_delete"


def test_upsert_usdt_via_holdings_rejected(db):
    with pytest.raises(svc.PortfolioError) as exc:
        svc.upsert_holding(db, asset="usdt", quantity="10", average_cost="1")
    assert exc.value.code == "invalid_config"
    assert repo.count_snapshots(db) == 0


def test_unsupported_asset_rejected_state_unchanged(db):
    svc.set_funding(db, "1000")
    n = repo.count_snapshots(db)
    with pytest.raises(svc.PortfolioError) as exc:
        svc.upsert_holding(db, asset="notacoin", quantity="1", average_cost=None)
    assert exc.value.code == "invalid_config"
    snap = svc.build_snapshot(db)
    assert [h["asset"] for h in snap["holdings"]] == ["usdt"]
    assert repo.count_snapshots(db) == n


def test_allocation_does_not_change_btc_quantity(db):
    svc.set_funding(db, "1000")
    svc.upsert_holding(db, asset="btc", quantity="0.005", average_cost=None)
    svc.create_allocation(db, label="A", reserved_size="250", target_ref=None)
    snap = svc.build_snapshot(db)
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.005"
    assert snap["reserved"] == "250"
    assert snap["cash"] == "1000"
    assert snap["available"] == "750"
