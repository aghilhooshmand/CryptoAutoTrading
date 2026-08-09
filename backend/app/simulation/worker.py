"""Background worker polling RUNNING simulation sessions."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.db import session as db_session
from app.simulation.clock import SystemClock
from app.simulation.pipeline import process_session_tick
from app.simulation.session_service import get_active_session

logger = logging.getLogger(__name__)

_task: Optional[asyncio.Task] = None
_stop = asyncio.Event()


async def _loop() -> None:
    clock = SystemClock()
    while not _stop.is_set():
        db = db_session.SessionLocal()
        try:
            row = get_active_session(db)
            if row is not None and row.state == "RUNNING":
                await process_session_tick(db, row, clock)
        except Exception:  # noqa: BLE001
            logger.exception("simulation worker tick failed")
        finally:
            db.close()
        try:
            await asyncio.wait_for(_stop.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass


def ensure_worker_running() -> None:
    global _task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _task is None or _task.done():
        _stop.clear()
        _task = loop.create_task(_loop())


def stop_worker() -> None:
    _stop.set()
