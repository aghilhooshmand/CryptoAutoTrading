"""Unit tests for Real pending confirmation TTL (Feature 015)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.simulation.pending_confirmation import (
    PENDING_TTL,
    create_pending,
    discard_pending,
    expire_if_due,
    get_active_pending,
)


def _db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/p.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_pending_expires_after_five_minutes(tmp_path):
    db = _db(tmp_path)
    created = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row = create_pending(
        db,
        session_id="11111111-1111-1111-1111-111111111111",
        symbol="btc_usdt",
        proposed_notional="10",
        reference_price="65000",
        now=created,
    )
    db.commit()
    assert row.status == "pending"
    assert row.expires_at == created + PENDING_TTL

    still = expire_if_due(db, row, now=created + timedelta(minutes=4, seconds=59))
    assert still.status == "pending"

    expired = expire_if_due(db, row, now=created + timedelta(minutes=5))
    assert expired.status == "expired"
    assert get_active_pending(db, row.session_id) is None


def test_expired_intent_not_reusable(tmp_path):
    db = _db(tmp_path)
    sid = "22222222-2222-2222-2222-222222222222"
    created = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    row = create_pending(
        db,
        session_id=sid,
        symbol="btc_usdt",
        proposed_notional="10",
        reference_price="65000",
        now=created,
    )
    expire_if_due(db, row, now=created + timedelta(minutes=6))
    db.commit()
    with pytest.raises(ValueError, match="pending_not_active"):
        discard_pending(db, row, status="confirmed")


def test_at_most_one_pending(tmp_path):
    db = _db(tmp_path)
    sid = "33333333-3333-3333-3333-333333333333"
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    create_pending(
        db,
        session_id=sid,
        symbol="btc_usdt",
        proposed_notional="10",
        reference_price="65000",
        now=now,
    )
    db.commit()
    with pytest.raises(ValueError, match="pending_already_exists"):
        create_pending(
            db,
            session_id=sid,
            symbol="btc_usdt",
            proposed_notional="11",
            reference_price="65000",
            now=now,
        )
