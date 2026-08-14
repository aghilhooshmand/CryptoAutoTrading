"""Contract tests for Feature 009 /portfolio API."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base
from app.main import app
from app.portfolio.valuation import QuoteView


def _default_quotes(assets, **_kwargs):
    out: dict[str, QuoteView] = {}
    for raw in assets:
        asset = raw.lower()
        if asset == "usdt":
            out[asset] = QuoteView(price=Decimal("1"), status="fresh")
        elif asset == "btc":
            out[asset] = QuoteView(price=Decimal("90000"), status="fresh")
        elif asset == "eth":
            out[asset] = QuoteView(price=Decimal("3000"), status="fresh")
        else:
            out[asset] = QuoteView(price=None, status="unavailable")
    return out


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    async def fake_fetch(assets, **kwargs):
        return _default_quotes(assets, **kwargs)

    monkeypatch.setattr("app.api.portfolio.fetch_quotes", fake_fetch)
    monkeypatch.setattr("app.portfolio.valuation.fetch_quotes", fake_fetch)
    with TestClient(app) as c:
        yield c


def _assert_invariants(data: dict) -> None:
    cash = float(data["cash"])
    reserved = float(data["reserved"])
    available = float(data["available"])
    assert abs(available - (cash - reserved)) < 1e-9
    assert sum(float(a["reservedSize"]) for a in data["allocations"]) == pytest.approx(reserved)
    usdt = next((h for h in data.get("holdings", []) if h["asset"] == "usdt"), None)
    if usdt is not None:
        assert usdt["quantity"] == data["cash"]
    else:
        assert data["cash"] == "0"
    valued = [h for h in data.get("holdings", []) if h.get("marketValue") is not None]
    equity = sum(float(h["marketValue"]) for h in valued)
    assert abs(equity - float(data["equity"])) < 1e-9
    assert data["equityComplete"] is (len(data.get("unvaluedAssets", [])) == 0)
    assert "equityComplete" in data


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
    assert data["holdings"] == []
    assert data["equityComplete"] is True
    assert data["warning"] is None
    assert data["bookProvenance"] == "simulation"
    assert data["mode"] == "simulation"
    assert data["totalPnl"] == "0"
    assert data["totalReturn"] is None
    _assert_invariants(data)


def test_put_funding_valid(client):
    r = client.put("/portfolio/funding", json={"cash": "1000"})
    assert r.status_code == 200
    data = r.json()
    assert data["cash"] == "1000"
    assert data["available"] == "1000"
    assert data["equity"] == "1000"
    assert data["equityComplete"] is True
    usdt = next(h for h in data["holdings"] if h["asset"] == "usdt")
    assert usdt["quantity"] == "1000"
    assert usdt["provenance"] == "simulation"
    assert usdt["unrealizedPnl"] is None
    assert usdt["return"] is None
    assert data["bookProvenance"] == "simulation"
    assert data["mode"] == "simulation"
    assert data["totalPnl"] == "0"
    assert data["totalReturn"] == "0"
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


def test_holdings_operator_upsert_removed(client):
    client.put("/portfolio/funding", json={"cash": "500"})
    r = client.put(
        "/portfolio/holdings",
        json={"asset": "btc", "quantity": "0.005", "averageCost": "80000"},
    )
    assert r.status_code == 404
    d = client.delete("/portfolio/holdings/btc")
    assert d.status_code == 404
    snap = client.get("/portfolio").json()
    assert [h["asset"] for h in snap["holdings"]] == ["usdt"]
    assert snap["bookProvenance"] == "simulation"
    _assert_invariants(snap)


def _apply_btc_fill(client, *, qty="0.005", cash_delta="-400", price="80000"):
    from app.db import session as db_session
    from app.portfolio import service as svc

    db = db_session.SessionLocal()
    try:
        svc.apply_simulation_fill(
            db,
            asset="btc",
            side="BUY",
            qty=qty,
            cash_delta=cash_delta,
            fill_price=price,
        )
    finally:
        db.close()
    return client.get("/portfolio").json()


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

    bad = client.post(
        "/portfolio/allocations",
        json={"label": "Too much", "reservedSize": "600"},
    )
    assert bad.status_code == 400
    assert client.get("/portfolio").json()["reserved"] == "500"

    patched = client.patch(
        f"/portfolio/allocations/{alloc_id}",
        json={"reservedSize": "200"},
    )
    assert patched.status_code == 200
    assert patched.json()["reserved"] == "450"
    _assert_invariants(patched.json())

    deleted = client.delete(f"/portfolio/allocations/{alloc_id}")
    assert deleted.status_code == 200
    assert deleted.json()["reserved"] == "250"
    _assert_invariants(deleted.json())


def test_allocations_leave_holdings_unchanged(client):
    client.put("/portfolio/funding", json={"cash": "1000"})
    data = _apply_btc_fill(client)
    assert next(h for h in data["holdings"] if h["asset"] == "btc")["quantity"] == "0.005"
    r = client.post(
        "/portfolio/allocations",
        json={"label": "A", "reservedSize": "250", "targetRef": "rsi"},
    )
    assert r.status_code == 201
    data = r.json()
    btc = next(h for h in data["holdings"] if h["asset"] == "btc")
    assert btc["quantity"] == "0.005"
    assert data["cash"] == "600"
    assert data["reserved"] == "250"
    _assert_invariants(data)

    over = client.post(
        "/portfolio/allocations",
        json={"label": "Too much", "reservedSize": "900"},
    )
    assert over.status_code == 400
    again = client.get("/portfolio").json()
    assert again["reserved"] == "250"
    assert next(h for h in again["holdings"] if h["asset"] == "btc")["quantity"] == "0.005"


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
    _apply_btc_fill(client)
    client.post(
        "/portfolio/allocations",
        json={"label": "Keep", "reservedSize": "300", "targetRef": "macd"},
    )
    assert (
        client.post(
            "/portfolio/allocations",
            json={"label": "No", "reservedSize": "900"},
        ).status_code
        == 400
    )
    again = client.get("/portfolio").json()
    assert again["cash"] == "600"
    assert again["reserved"] == "300"
    assert len(again["allocations"]) == 1
    assert again["allocations"][0]["label"] == "Keep"
    assert next(h for h in again["holdings"] if h["asset"] == "btc")["quantity"] == "0.005"
    _assert_invariants(again)


def test_get_does_not_append_snapshot(client):
    from app.db import session as db_session
    from app.portfolio import repository as repo

    client.put("/portfolio/funding", json={"cash": "100"})
    db = db_session.SessionLocal()
    try:
        before = repo.count_snapshots(db)
    finally:
        db.close()
    client.get("/portfolio")
    client.get("/portfolio")
    db = db_session.SessionLocal()
    try:
        assert repo.count_snapshots(db) == before
    finally:
        db.close()


def test_missing_quote_marks_equity_incomplete(client, monkeypatch):
    async def missing(assets, **kwargs):
        out = {}
        for raw in assets:
            asset = raw.lower()
            if asset == "usdt":
                out[asset] = QuoteView(price=Decimal("1"), status="fresh")
            else:
                out[asset] = QuoteView(price=None, status="unavailable")
        return out

    monkeypatch.setattr("app.api.portfolio.fetch_quotes", missing)
    client.put("/portfolio/funding", json={"cash": "1000"})
    _apply_btc_fill(client)
    snap = client.get("/portfolio").json()
    assert snap["equityComplete"] is False
    assert "btc" in snap["unvaluedAssets"]
    assert snap["equity"] == "600"
    assert snap["totalPnl"] is None
    assert snap["totalReturn"] is None


def test_stale_quote_included(client, monkeypatch):
    async def stale(assets, **kwargs):
        out = {}
        for raw in assets:
            asset = raw.lower()
            if asset == "usdt":
                out[asset] = QuoteView(price=Decimal("1"), status="fresh")
            elif asset == "btc":
                out[asset] = QuoteView(price=Decimal("90000"), status="stale")
            else:
                out[asset] = QuoteView(price=None, status="unavailable")
        return out

    monkeypatch.setattr("app.api.portfolio.fetch_quotes", stale)
    client.put("/portfolio/funding", json={"cash": "1000"})
    _apply_btc_fill(client)
    snap = client.get("/portfolio").json()
    btc = next(h for h in snap["holdings"] if h["asset"] == "btc")
    assert btc["priceStatus"] == "stale"
    assert snap["equity"] == "1050"
    assert snap["equityComplete"] is True


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
