"""FastAPI application entry for CryptoAutoTrading."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.api.health import router as health_router
from app.api.market_data import router as market_data_router
from app.api.backtest import router as backtest_router
from app.api.comparison import router as comparison_router
from app.api.portfolio import router as portfolio_router
from app.api.settings import router as settings_router
from app.api.simulation import router as simulation_router
from app.api.strategies import router as strategies_router
from app.api.account import router as account_router
from app.api.xt_account import router as xt_account_router
from app.db import session as db_session
from app.simulation.recovery import recover_orphan_sessions_async
from app.simulation.worker import ensure_worker_running, stop_worker
# Ensure all strategies register before serving
from app.strategy import (  # noqa: F401
    bollinger,
    breakout,
    dual_ema,
    macd,
    rsi,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_session.init_db()
    db = db_session.SessionLocal()
    try:
        await recover_orphan_sessions_async(db)
    finally:
        db.close()
    ensure_worker_running()
    yield
    stop_worker()


app = FastAPI(title="CryptoAutoTrading API", version="0.9.0", lifespan=lifespan)

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(market_data_router)
api_router.include_router(strategies_router)
api_router.include_router(simulation_router)
api_router.include_router(backtest_router)
api_router.include_router(comparison_router)
api_router.include_router(settings_router)
api_router.include_router(portfolio_router)
api_router.include_router(account_router)
api_router.include_router(xt_account_router)
app.include_router(api_router)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
