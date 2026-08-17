"""Same recorded candles → same engine outcome regardless of venue labels (FR-032)."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.backtest import service as svc
from app.db.models import Base
from app.market_data.models import CandleInterval, Candlestick


def _candles(n: int = 40) -> list[Candlestick]:
    out = []
    px = 100.0
    start = 1_700_000_000_000
    for i in range(n):
        px += 0.6 if i < 20 else -0.8
        out.append(
            Candlestick(
                openTime=start + i * 3_600_000,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px),
            )
        )
    return out


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/inv.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()


def test_recorded_candles_invariance_across_venues(db) -> None:
    candles = _candles()
    xt = svc.validate_config(
        {
            "symbol": "btc_usdt",
            "timeframe": "1h",
            "startTime": 1_700_000_000_000,
            "endTime": 1_700_000_000_000 + 40 * 3_600_000,
            "startingCapital": "1000",
            "allocatedCapital": "1000",
            "maxPositionSize": "1000",
            "strategyId": "dual_ema",
        }
    )
    kraken = svc.validate_config(
        {
            "symbol": "BTC/EUR",
            "venue": "kraken",
            "baseAsset": "BTC",
            "quoteAsset": "EUR",
            "canonicalSymbol": "BTC/EUR",
            "venueProductId": "XXBTZEUR",
            "timeframe": "1h",
            "startTime": 1_700_000_000_000,
            "endTime": 1_700_000_000_000 + 40 * 3_600_000,
            "startingCapital": "1000",
            "allocatedCapital": "1000",
            "maxPositionSize": "1000",
            "strategyId": "dual_ema",
        }
    )
    xt_params = xt.pop("strategy_params_obj")
    kraken_params = kraken.pop("strategy_params_obj")
    xt.pop("min_history_candles")
    kraken.pop("min_history_candles")
    xt_out = svc.run_leg_with_prefetched_candles(
        db, fields=xt, strategy_params_obj=xt_params, candles=candles, wire_shared=False
    )
    kraken_out = svc.run_leg_with_prefetched_candles(
        db, fields=kraken, strategy_params_obj=kraken_params, candles=candles, wire_shared=False
    )
    assert xt_out["status"] == "completed"
    assert kraken_out["status"] == "completed"
    assert xt_out["summary"]["netPnl"] == kraken_out["summary"]["netPnl"]
    assert xt_out["summary"]["tradeCount"] == kraken_out["summary"]["tradeCount"]
    assert xt_out["venue"] == "xt"
    assert kraken_out["venue"] == "kraken"
