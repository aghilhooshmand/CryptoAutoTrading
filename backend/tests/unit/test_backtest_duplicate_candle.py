"""Duplicate openTime candles are skipped once (FR-008)."""

from __future__ import annotations

from decimal import Decimal

from app.backtest.engine import run_engine
from app.market_data.models import Candlestick
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtest import repository as repo
from app.db.models import Base


def test_duplicate_candle_skipped(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/dup.db", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = Session()
    start = 1_700_000_000_000
    step = 3_600_000
    candles = []
    px = 100.0
    for i in range(30):
        px += 0.3
        candles.append(
            Candlestick(
                openTime=start + i * step,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px),
            )
        )
    # Duplicate of candle index 10
    dup = candles[10]
    candles.insert(11, Candlestick(openTime=dup.openTime, open=dup.open, high=dup.high, low=dup.low, close=dup.close))
    fields = {
        "symbol": "btc_usdt",
        "timeframe": "1h",
        "start_time": start,
        "end_time": start + 40 * step,
        "starting_capital": "1000",
        "allocated_capital": "1000",
        "max_position_size": "1000",
        "target_net_profit_rate": None,
        "max_session_loss_rate": None,
        "target_net_profit_amount": None,
        "max_session_loss_amount": None,
        "max_trades": None,
        "fee_rate": "0.001",
        "slippage_rate": "0.0005",
        "strategy_id": "dual_ema_9_21",
    }
    run = repo.create_running_run(db, fields)
    summary = run_engine(
        db,
        run.id,
        candles,
        starting_capital=Decimal("1000"),
        allocated_capital=Decimal("1000"),
        max_position_size=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        max_trades=None,
        target_net_profit_amount=None,
        max_session_loss_amount=None,
        wire_shared=True,
    )
    assert summary is not None
    # Decisions should not exceed unique candle count (duplicates skipped)
    from app.db.models import BacktestDecisionRow

    n = db.query(BacktestDecisionRow).filter_by(run_id=run.id).count()
    assert n <= 30
    db.close()
