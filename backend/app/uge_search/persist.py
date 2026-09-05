"""Persist / load frozen UGE run artifacts (Feature 019 US3)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.uge_search.errors import PERSIST_FAILED, UgeSearchError
from app.uge_search.runner import UgeRunResult

DEFAULT_UGE_RUNS_DIR = Path(__file__).resolve().parents[2] / "data" / "uge_runs"


def uge_runs_dir(base: Path | None = None) -> Path:
    path = base if base is not None else DEFAULT_UGE_RUNS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def persist_run_result(
    result: UgeRunResult,
    *,
    directory: Path | None = None,
    artifact_id: str | None = None,
) -> Path:
    """Write frozen phenotype JSON; returns path."""
    if not result.best_phenotype:
        raise UgeSearchError(PERSIST_FAILED, "No best phenotype to persist")
    dir_path = uge_runs_dir(directory)
    aid = artifact_id or str(uuid.uuid4())
    payload: dict[str, Any] = {
        "id": aid,
        "phenotype": result.best_phenotype,
        "trainFitness": result.train_fitness,
        "validationFitness": result.validation_fitness,
        "testFitness": result.test_fitness,
        "fitnessId": result.fitness_id,
        "seed": result.seed,
        "grammarId": result.grammar_id,
        "split": result.split,
        "status": result.status,
        "populationSize": result.population_size,
        "nGenerations": result.n_generations,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    path = dir_path / f"{aid}.json"
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise UgeSearchError(PERSIST_FAILED, str(exc)) from exc
    return path


def load_frozen_artifact(path: Path | str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UgeSearchError(PERSIST_FAILED, f"Cannot load artifact: {exc}") from exc
    if not isinstance(data, dict) or "phenotype" not in data:
        raise UgeSearchError(PERSIST_FAILED, "Artifact missing phenotype")
    return data


def load_frozen_phenotype(path: Path | str) -> str:
    return str(load_frozen_artifact(path)["phenotype"])


def list_frozen_artifacts(directory: Path | None = None) -> list[dict[str, Any]]:
    dir_path = uge_runs_dir(directory)
    out: list[dict[str, Any]] = []
    for path in sorted(dir_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = load_frozen_artifact(path)
            data["path"] = str(path)
            out.append(data)
        except UgeSearchError:
            continue
    return out
