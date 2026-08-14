"""Unit tests for Feature 009 portfolio identity and service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PortfolioRow
from app.portfolio import identity
from app.portfolio import service as svc


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()


def test_available_equals_cash_minus_reserved():
    cash = Decimal("1000")
    reserved = Decimal("400")
    assert identity.available_from(cash, reserved) == Decimal("600")
    assert identity.assert_invariants(cash, reserved) == Decimal("600")


def test_reserved_cannot_exceed_cash():
    with pytest.raises(identity.CapitalIdentityError):
        identity.assert_invariants(Decimal("100"), Decimal("150"))


def test_sum_reserved():
    assert identity.sum_reserved(["100", "250.5", "0.5"]) == Decimal("351")


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
        # Routers are not invoked via service path
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
