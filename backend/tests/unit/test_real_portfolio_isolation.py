"""Real fills must not mutate Simulation Portfolio (Feature 015 US3 / FR-001a)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.execution.real import set_client_factory_override
from app.market_data.models import MarketQuote, MarketStatus
from app.portfolio.repository import list_holdings
from app.simulation.clock import FakeClock
from app.simulation.pending_confirmation import create_pending
from app.simulation.real_gates import set_try_free_usdt_override
from app.simulation.session_service import confirm_entry_async, create_session


class FillingXtClient:
    def __init__(self) -> None:
        self.place_calls: list[dict] = []

    async def place_market_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return {"orderId": "xt-buy-1"}

    async def get_order(self, order_id: str):
        return {
            "orderId": order_id,
            "symbol": "btc_usdt",
            "side": "BUY",
            "status": "FILLED",
            "executedQty": "0.00038461",
            "price": "65000",
        }

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/iso.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    set_try_free_usdt_override(lambda: Decimal("100"))
    s = TestingSession()
    from app.portfolio import service as portfolio_svc

    portfolio_svc.set_funding(s, "100000")
    try:
        yield s
    finally:
        s.close()
        set_try_free_usdt_override(None)
        set_client_factory_override(None)


def _holdings(db):
    return {(h.asset, h.quantity, h.provenance) for h in list_holdings(db)}


def test_real_confirmed_buy_does_not_mutate_portfolio(db):
    before = _holdings(db)
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    row = create_session(
        db,
        {
            "mode": "real",
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "allocatedCapital": "25",
            "maxPositionSize": "25",
            "targetNetProfitRate": "0.01",
            "maxSessionLossRate": "0.007",
            "maxTrades": 20,
            "durationSeconds": 3600,
            "strategyId": "dual_ema",
        },
    )
    row.state = "RUNNING"
    row.started_at = now
    create_pending(
        db,
        session_id=row.id,
        symbol=row.symbol,
        proposed_notional="25",
        reference_price="65000",
        now=now,
    )
    db.commit()
    assert _holdings(db) == before

    fake = FillingXtClient()
    set_client_factory_override(lambda _c: fake)
    quote = MarketQuote(
        symbol="btc_usdt",
        lastPrice="65000",
        source="XT",
        observedAt=now,
        retrievedAt=now,
        status=MarketStatus.FRESH,
    )
    mock = AsyncMock()
    mock.get_quote = AsyncMock(return_value=quote)
    with patch("app.simulation.session_service.get_market_data_service", return_value=mock):
        updated = asyncio.run(confirm_entry_async(db, row.id, clock=FakeClock(now)))
    assert updated.position_side == "long"
    assert len(fake.place_calls) == 1
    assert _holdings(db) == before
