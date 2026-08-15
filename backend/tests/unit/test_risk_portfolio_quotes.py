"""Portfolio Risk context must use Feature 002 quotes when valuing holdings."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PortfolioHoldingRow, SimulationSessionRow
from app.portfolio import repository as portfolio_repo
from app.portfolio.valuation import QuoteView
from app.simulation.portfolio_risk import apply_portfolio_context, freeze_portfolio_loss_baseline


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/q.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    portfolio_repo.ensure_portfolio(session)
    portfolio_repo.migrate_cash_to_usdt(session)
    # Fund USDT + BTC holding
    usdt = portfolio_repo.get_holding(session, "usdt")
    if usdt is None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        session.add(
            PortfolioHoldingRow(
                id="11111111-1111-1111-1111-111111111111",
                portfolio_id=1,
                asset="usdt",
                quantity="600",
                average_cost=None,
                realized_pnl="0",
                provenance="simulation",
                created_at=now,
                updated_at=now,
            )
        )
    else:
        usdt.quantity = "600"
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    session.add(
        PortfolioHoldingRow(
            id="22222222-2222-2222-2222-222222222222",
            portfolio_id=1,
            asset="btc",
            quantity="0.01",
            average_cost="50000",
            realized_pnl="0",
            provenance="simulation",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    yield session
    session.close()


def test_apply_portfolio_context_values_holdings_with_quotes(db):
    row = SimulationSessionRow(
        id="33333333-3333-3333-3333-333333333333",
        mode="simulation",
        state="RUNNING",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="500",
        max_position_size="500",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.01",
        target_net_profit_amount="5",
        max_session_loss_amount="5",
        max_trades=10,
        duration_seconds=3600,
        fee_rate="0.001",
        slippage_rate="0.0005",
        strategy_id="dual_ema",
        cash="500",
        position_side="flat",
        position_qty="0",
        trade_count=0,
        strategy_fill_count=0,
        cumulative_fees="0",
        cumulative_slippage_cost="0",
        cumulative_gross_realized="0",
        position_flatten_status="n/a",
        per_symbol_max_weight="0.5",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    quotes = {
        "usdt": QuoteView(price=Decimal("1"), status="fresh"),
        "btc": QuoteView(price=Decimal("50000"), status="fresh"),
    }
    kwargs = apply_portfolio_context({}, db=db, row=row, quotes=quotes)
    assert kwargs["portfolio_equity_complete"] is True
    assert kwargs["portfolio_current_equity"] == Decimal("1100")  # 600 + 500
    btc = next(h for h in kwargs["holdings"] if h.asset == "btc")
    assert btc.market_value == Decimal("500")


def test_freeze_baseline_uses_equity_when_quotes_complete(db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    row = SimulationSessionRow(
        id="44444444-4444-4444-4444-444444444444",
        mode="simulation",
        state="CONFIGURED",
        symbol="btc_usdt",
        timeframe="1h",
        starting_capital="1000",
        allocated_capital="500",
        max_position_size="500",
        target_net_profit_rate="0.01",
        max_session_loss_rate="0.01",
        target_net_profit_amount="5",
        max_session_loss_amount="5",
        max_trades=10,
        duration_seconds=3600,
        fee_rate="0.001",
        slippage_rate="0.0005",
        strategy_id="dual_ema",
        cash="500",
        position_side="flat",
        position_qty="0",
        trade_count=0,
        strategy_fill_count=0,
        cumulative_fees="0",
        cumulative_slippage_cost="0",
        cumulative_gross_realized="0",
        position_flatten_status="n/a",
        portfolio_max_loss_rate="0.1",
        created_at=now,
        updated_at=now,
    )
    quotes = {
        "usdt": QuoteView(price=Decimal("1"), status="fresh"),
        "btc": QuoteView(price=Decimal("50000"), status="fresh"),
    }
    freeze_portfolio_loss_baseline(db, row, quotes=quotes)
    assert row.portfolio_loss_baseline_kind == "equity"
    assert row.portfolio_loss_baseline_value == "1100"
    assert Decimal(row.portfolio_max_loss_amount) == Decimal("110")
