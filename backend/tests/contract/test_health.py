"""Contract tests for GET /health (SC-004)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_healthy_within_two_seconds() -> None:
    started = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json() == {"status": "healthy"}
    assert elapsed < 2.0, f"Health check took {elapsed:.3f}s (SC-004 requires < 2s)"
