"""SQLite engine and session factory for simulation domain state."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data"
_DEFAULT_PATH = _DEFAULT_DIR / "simulation.db"


def db_path() -> Path:
    raw = os.environ.get("SIMULATION_DB_PATH")
    if raw:
        return Path(raw)
    return _DEFAULT_PATH


def make_engine(url: str | None = None):
    if url is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    return create_engine(url, connect_args={"check_same_thread": False})


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Session:
    return SessionLocal()


def init_db() -> None:
    from app.db import models  # noqa: F401
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
