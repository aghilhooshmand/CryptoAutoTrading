"""Unknown stored strategy_id: READ ok, START forbidden."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.models import Base, SimulationSessionRow
from app.main import app
from app.market_data.models import MarketQuote, MarketStatus


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/u.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    async def _quote(symbol: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=symbol,
            lastPrice="65000.00",
            source="XT",
            observedAt=now,
            retrievedAt=now,
            status=MarketStatus.FRESH,
        )

    mock_svc = AsyncMock()
    mock_svc.get_quote = AsyncMock(side_effect=_quote)
    with patch("app.simulation.session_service.get_market_data_service", return_value=mock_svc):
        with patch("app.simulation.worker.ensure_worker_running"):
            with TestClient(app) as c:
                yield c, TestingSession


def test_get_unknown_strategy_allowed_start_forbidden(client):
    c, Session = client
    db = Session()
    now = datetime.now(timezone.utc)
    row = SimulationSessionRow(
        id="11111111-1111-1111-1111-111111111111",
        mode="simulation",
        state="CONFIGURED",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="500",
        allocated_capital="500",
        max_position_size="500",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.007",
        target_net_profit_amount="5",
        max_session_loss_amount="3.5",
        max_trades=20,
        duration_seconds=3600,
        fee_rate="0.001",
        slippage_rate="0.0005",
        strategy_id="deleted_strategy_x",
        strategy_params=None,
        cash="500",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.close()

    got = c.get("/simulation/sessions/11111111-1111-1111-1111-111111111111")
    assert got.status_code == 200
    assert got.json()["strategyId"] == "deleted_strategy_x"

    started = c.post("/simulation/sessions/11111111-1111-1111-1111-111111111111/start")
    assert started.status_code == 400
    assert started.json()["detail"]["error"]["code"] == "unknown_strategy"
