"""Contract tests for Feature 009 /portfolio API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    with TestClient(app) as c:
        yield c


def _assert_invariants(data: dict) -> None:
    cash = float(data["cash"])
    reserved = float(data["reserved"])
    available = float(data["available"])
    assert abs(available - (cash - reserved)) < 1e-9
    assert sum(float(a["reservedSize"]) for a in data["allocations"]) == pytest.approx(reserved)
    assert data["deployed"] == "0"
    assert data["positions"] == []


def test_get_unfunded_empty(client):
    r = client.get("/portfolio")
    assert r.status_code == 200
    data = r.json()
    assert data["cash"] == "0"
    assert data["reserved"] == "0"
    assert data["available"] == "0"
    assert data["deployed"] == "0"
    assert data["positions"] == []
    assert data["allocations"] == []
    assert data["warning"] is None
    _assert_invariants(data)


def test_put_funding_valid(client):
    r = client.put("/portfolio/funding", json={"cash": "1000"})
    assert r.status_code == 200
    data = r.json()
    assert data["cash"] == "1000"
    assert data["available"] == "1000"
    assert data["equity"] == "1000"
    _assert_invariants(data)


def test_put_funding_negative_rejected(client):
    client.put("/portfolio/funding", json={"cash": "500"})
    r = client.put("/portfolio/funding", json={"cash": "-1"})
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "invalid_config"
    again = client.get("/portfolio").json()
    assert again["cash"] == "500"


def test_put_funding_invalid_rejected(client):
    client.put("/portfolio/funding", json={"cash": "100"})
    r = client.put("/portfolio/funding", json={"cash": "abc"})
    assert r.status_code == 400
    assert client.get("/portfolio").json()["cash"] == "100"


def test_allocations_crud_and_invariants(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    r = client.post(
        "/portfolio/allocations",
        json={"label": "RSI sleeve", "reservedSize": "250", "targetRef": "rsi"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["reserved"] == "250"
    assert data["available"] == "750"
    assert len(data["allocations"]) == 1
    alloc_id = data["allocations"][0]["id"]
    _assert_invariants(data)

    # Same targetRef allowed
    r2 = client.post(
        "/portfolio/allocations",
        json={"label": "RSI sleeve 2", "reservedSize": "250", "targetRef": "rsi"},
    )
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["reserved"] == "500"
    assert len(data2["allocations"]) == 2
    assert all(a["targetRef"] == "rsi" for a in data2["allocations"])
    _assert_invariants(data2)

    # Over-reserve rejected
    bad = client.post(
        "/portfolio/allocations",
        json={"label": "Too much", "reservedSize": "600"},
    )
    assert bad.status_code == 400
    assert client.get("/portfolio").json()["reserved"] == "500"

    # Resize
    patched = client.patch(
        f"/portfolio/allocations/{alloc_id}",
        json={"reservedSize": "200"},
    )
    assert patched.status_code == 200
    assert patched.json()["reserved"] == "450"
    _assert_invariants(patched.json())

    # Delete
    deleted = client.delete(f"/portfolio/allocations/{alloc_id}")
    assert deleted.status_code == 200
    assert deleted.json()["reserved"] == "250"
    _assert_invariants(deleted.json())


def test_funding_reject_when_cash_less_than_reserved(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    client.post(
        "/portfolio/allocations",
        json={"label": "A", "reservedSize": "500"},
    )
    r = client.put("/portfolio/funding", json={"cash": "400"})
    assert r.status_code == 400
    err = r.json()["detail"]["error"]
    assert err["code"] == "invalid_config"
    assert "reserved" in err["message"].lower()
    again = client.get("/portfolio").json()
    assert again["cash"] == "1000"
    assert again["reserved"] == "500"


def test_unknown_allocation_404(client):
    client.put("/portfolio/funding", json={"cash": "100"})
    assert client.patch(
        "/portfolio/allocations/11111111-1111-1111-1111-111111111111",
        json={"reservedSize": "10"},
    ).status_code == 404
    assert client.delete(
        "/portfolio/allocations/11111111-1111-1111-1111-111111111111"
    ).status_code == 404


def test_persistence_across_get(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    client.post(
        "/portfolio/allocations",
        json={"label": "Keep", "reservedSize": "300", "targetRef": "macd"},
    )
    # Failed mutation
    assert (
        client.post(
            "/portfolio/allocations",
            json={"label": "No", "reservedSize": "900"},
        ).status_code
        == 400
    )
    again = client.get("/portfolio").json()
    assert again["cash"] == "1000"
    assert again["reserved"] == "300"
    assert len(again["allocations"]) == 1
    assert again["allocations"][0]["label"] == "Keep"
    _assert_invariants(again)


def test_corrupt_allocation_get_and_mutations(client):
    """Corrupt reservedSize must not invent available; mutations return 400."""
    from datetime import datetime, timezone

    from app.db import session as db_session
    from app.db.models import PortfolioAllocationRow

    client.put("/portfolio/funding", json={"cash": "1000"})
    client.post(
        "/portfolio/allocations",
        json={"label": "ok", "reservedSize": "200"},
    )

    db = db_session.SessionLocal()
    try:
        now = datetime.now(timezone.utc)
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
    finally:
        db.close()

    snap = client.get("/portfolio").json()
    assert snap["warning"] is not None
    assert snap["available"] == "0"
    assert snap["reserved"] == "0"
    assert snap["cash"] == "1000"
    assert len(snap["allocations"]) == 2

    fund = client.put("/portfolio/funding", json={"cash": "1000"})
    assert fund.status_code == 400
    assert fund.json()["detail"]["error"]["code"] == "invalid_config"

    create = client.post(
        "/portfolio/allocations",
        json={"label": "more", "reservedSize": "10"},
    )
    assert create.status_code == 400

    again = client.get("/portfolio").json()
    assert again["cash"] == "1000"
    assert len(again["allocations"]) == 2
