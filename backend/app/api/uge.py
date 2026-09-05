"""UGE frozen-artifact API (Feature 019) — list/load for Backtest UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.uge_search.errors import UgeSearchError
from app.uge_search.persist import list_frozen_artifacts, load_frozen_artifact, uge_runs_dir

router = APIRouter(tags=["uge"])


@router.get("/uge/frozen")
def get_frozen_list() -> dict[str, Any]:
    artifacts = list_frozen_artifacts()
    # Slim payload for UI
    items = [
        {
            "id": a.get("id"),
            "phenotype": a.get("phenotype"),
            "trainFitness": a.get("trainFitness"),
            "validationFitness": a.get("validationFitness"),
            "fitnessId": a.get("fitnessId"),
            "seed": a.get("seed"),
            "createdAt": a.get("createdAt"),
            "path": a.get("path"),
        }
        for a in artifacts
    ]
    return {"artifacts": items, "directory": str(uge_runs_dir())}


@router.get("/uge/frozen/{artifact_id}")
def get_frozen_one(artifact_id: str) -> dict[str, Any]:
    path = uge_runs_dir() / f"{artifact_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Frozen artifact not found")
    try:
        data = load_frozen_artifact(path)
    except UgeSearchError as exc:
        raise HTTPException(status_code=400, detail=exc.to_error_dict()) from exc
    data["path"] = str(path)
    return data
