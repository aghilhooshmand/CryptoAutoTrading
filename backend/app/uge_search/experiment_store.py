"""Persist Evolution experiments + generation snapshots (Feature 020)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_EXPERIMENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "uge_experiments"

# Protects read-modify-write on meta.json and unique-tmp atomic replaces.
_META_LOCK = threading.RLock()


def experiments_dir(base: Path | None = None) -> Path:
    path = base if base is not None else DEFAULT_EXPERIMENTS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_experiment_id() -> str:
    return f"exp_{uuid.uuid4().hex[:16]}"


def experiment_path(experiment_id: str, base: Path | None = None) -> Path:
    return experiments_dir(base) / experiment_id


def write_meta(experiment_id: str, meta: dict[str, Any], base: Path | None = None) -> Path:
    """Atomically write meta.json using a unique temp name (safe under concurrency)."""
    root = experiment_path(experiment_id, base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "meta.json"
    tmp = root / f"meta.json.{uuid.uuid4().hex}.tmp"
    payload = json.dumps(meta, indent=2)
    with _META_LOCK:
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
    return path


def read_meta(experiment_id: str, base: Path | None = None) -> dict[str, Any] | None:
    path = experiment_path(experiment_id, base) / "meta.json"
    with _META_LOCK:
        if not path.is_file():
            return None
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return None
            return json.loads(text)
        except (OSError, json.JSONDecodeError):
            return None


def update_meta(experiment_id: str, patch: dict[str, Any], base: Path | None = None) -> dict[str, Any]:
    with _META_LOCK:
        meta = read_meta(experiment_id, base) or {}
        meta.update(patch)
        write_meta(experiment_id, meta, base)
        return meta


def append_generation(
    experiment_id: str,
    snapshot: dict[str, Any],
    base: Path | None = None,
) -> None:
    root = experiment_path(experiment_id, base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "generations.jsonl"
    row = dict(snapshot)
    row.setdefault("recordedAt", _now())
    with _META_LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def read_generations(experiment_id: str, base: Path | None = None) -> list[dict[str, Any]]:
    path = experiment_path(experiment_id, base) / "generations.jsonl"
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with _META_LOCK:
        text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def list_experiments(base: Path | None = None) -> list[dict[str, Any]]:
    root = experiments_dir(base)
    items: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        meta = read_meta(child.name, base)
        if meta:
            items.append(meta)
    items.sort(key=lambda m: str(m.get("createdAt") or ""), reverse=True)
    return items


def create_experiment_meta(
    *,
    experiment_id: str | None = None,
    config: dict[str, Any],
    status: str = "queued",
    base: Path | None = None,
) -> dict[str, Any]:
    eid = experiment_id or new_experiment_id()
    meta: dict[str, Any] = {
        "id": eid,
        "status": status,
        "createdAt": _now(),
        "startedAt": None,
        "finishedAt": None,
        "config": config,
        "grammarId": config.get("grammarId") or "trading_mvp",
        "bestPhenotype": None,
        "trainFitness": None,
        "validationFitness": None,
        "testFitness": None,
        "fitnessId": config.get("fitnessId"),
        "terminationReason": None,
        "errorMessage": None,
        "generationCount": 0,
    }
    write_meta(eid, meta, base)
    return meta
