"""FastAPI application entry for CryptoAutoTrading."""

from fastapi import APIRouter, FastAPI

from app.api.health import router as health_router
from app.api.market_data import router as market_data_router

app = FastAPI(title="CryptoAutoTrading API", version="0.2.0")

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(market_data_router)
app.include_router(api_router)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
