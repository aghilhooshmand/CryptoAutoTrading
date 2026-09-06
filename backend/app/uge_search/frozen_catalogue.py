"""Named frozen UGE strategies catalogue (Feature 020c)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.strategy.base import Strategy
from app.strategy.registry import StrategyRegistration, register
from app.torque_bind.bind import bind_phenotype, check_phenotype
from app.uge_search import experiment_store as store
from app.uge_search.errors import (
    DUPLICATE_DISPLAY_NAME,
    EXPERIMENT_NOT_FOUND,
    EXPERIMENT_NOT_TERMINAL,
    FREEZE_FAILED,
    UgeSearchError,
)

DEFAULT_FROZEN_DIR = Path(__file__).resolve().parents[2] / "data" / "uge_frozen_strategies"

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def frozen_dir(base: Path | None = None) -> Path:
    path = base if base is not None else DEFAULT_FROZEN_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(display_name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", display_name.strip().lower()).strip("_")
    return (s or "frozen")[:40]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_frozen_entries(base: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(frozen_dir(base).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("strategyId"):
                out.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return out


def display_name_taken(display_name: str, base: Path | None = None) -> bool:
    needle = display_name.strip().lower()
    return any(str(e.get("displayName", "")).strip().lower() == needle for e in list_frozen_entries(base))


def freeze_best_phenotype(
    experiment_id: str,
    display_name: str,
    *,
    base: Path | None = None,
    experiments_base: Path | None = None,
) -> dict[str, Any]:
    name = display_name.strip()
    if not name:
        raise UgeSearchError(FREEZE_FAILED, "displayName is required")
    if display_name_taken(name, base):
        raise UgeSearchError(DUPLICATE_DISPLAY_NAME, "Display name already used by a frozen strategy")

    meta = store.read_meta(experiment_id, experiments_base)
    if not meta:
        raise UgeSearchError(EXPERIMENT_NOT_FOUND, "Experiment not found")
    status = str(meta.get("status"))
    if status not in _TERMINAL:
        raise UgeSearchError(EXPERIMENT_NOT_TERMINAL, "Experiment must be terminal before freeze")
    phenotype = meta.get("bestPhenotype")
    if not phenotype or not str(phenotype).strip():
        raise UgeSearchError(FREEZE_FAILED, "No best phenotype to freeze")

    check = check_phenotype(str(phenotype))
    if not check.ok:
        msg = check.error.message if check.error else "Torque check failed"
        raise UgeSearchError(FREEZE_FAILED, msg)

    strategy_id = f"uge_frozen_{_slug(name)}_{uuid.uuid4().hex[:8]}"
    entry = {
        "strategyId": strategy_id,
        "displayName": name,
        "phenotype": str(phenotype),
        "sourceExperimentId": experiment_id,
        "seed": (meta.get("config") or {}).get("seed"),
        "fitnessId": meta.get("fitnessId"),
        "trainFitness": meta.get("trainFitness"),
        "validationFitness": meta.get("validationFitness"),
        "createdAt": _now(),
    }
    path = frozen_dir(base) / f"{strategy_id}.json"
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    register_frozen_entry(entry)
    return entry


def register_frozen_entry(entry: dict[str, Any]) -> None:
    phenotype = str(entry["phenotype"])
    strategy_id = str(entry["strategyId"])
    display_name = str(entry.get("displayName") or strategy_id)

    def _factory(_params: dict[str, Any]) -> Strategy:
        return bind_phenotype(phenotype)

    register(
        StrategyRegistration(
            strategy_id=strategy_id,
            display_name=display_name,
            aliases=[],
            parameters=[],
            constraints=[],
            factory=_factory,
        )
    )


def load_and_register_all(base: Path | None = None) -> int:
    n = 0
    for entry in list_frozen_entries(base):
        try:
            register_frozen_entry(entry)
            n += 1
        except Exception:  # noqa: BLE001
            continue
    return n
