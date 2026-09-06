"""UGE frozen-artifact API (019) + Evolution experiments API (020)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app.uge_search.errors import (
    DUPLICATE_DISPLAY_NAME,
    EXPERIMENT_NOT_FOUND,
    EXPERIMENT_NOT_TERMINAL,
    INVALID_EXPERIMENT_CONFIG,
    INVALID_SEARCH_SPACE,
    UgeSearchError,
)
from app.uge_search.experiment_runner import ExperimentConflictError
from app.uge_search.experiment_service import (
    cancel_experiment,
    create_experiment,
    get_experiment,
    list_experiments,
)
from app.uge_search.frozen_catalogue import freeze_best_phenotype
from app.uge_search.persist import list_frozen_artifacts, load_frozen_artifact, uge_runs_dir

router = APIRouter(tags=["uge"])


@router.get("/uge/frozen")
def get_frozen_list() -> dict[str, Any]:
    artifacts = list_frozen_artifacts()
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


@router.post("/uge/experiments", status_code=202)
async def post_experiment(body: dict[str, Any]) -> dict[str, Any]:
    try:
        return await create_experiment(body)
    except ExperimentConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc
    except UgeSearchError as exc:
        code = 400
        if exc.code == INVALID_SEARCH_SPACE:
            code = 400
        raise HTTPException(status_code=code, detail=exc.to_error_dict()) from exc


@router.get("/uge/experiments")
def get_experiments() -> dict[str, Any]:
    return {"experiments": list_experiments()}


@router.get("/uge/experiments/{experiment_id}")
def get_one_experiment(experiment_id: str) -> dict[str, Any]:
    meta = get_experiment(experiment_id, include_generations=True)
    if not meta:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return meta


@router.get("/uge/experiments/{experiment_id}/generations")
def get_experiment_generations(experiment_id: str) -> dict[str, Any]:
    meta = get_experiment(experiment_id, include_generations=True)
    if not meta:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"experimentId": experiment_id, "generations": meta.get("generations") or []}


@router.post("/uge/experiments/{experiment_id}/cancel")
def post_cancel(experiment_id: str) -> dict[str, Any]:
    try:
        return cancel_experiment(experiment_id)
    except UgeSearchError as exc:
        status = 404 if exc.code == EXPERIMENT_NOT_FOUND else 409
        raise HTTPException(status_code=status, detail=exc.to_error_dict()) from exc


@router.post("/uge/experiments/{experiment_id}/freeze", status_code=201)
def post_freeze(experiment_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    display_name = str(body.get("displayName") or "").strip()
    try:
        return freeze_best_phenotype(experiment_id, display_name)
    except UgeSearchError as exc:
        if exc.code == EXPERIMENT_NOT_FOUND:
            raise HTTPException(status_code=404, detail=exc.to_error_dict()) from exc
        if exc.code in (EXPERIMENT_NOT_TERMINAL, DUPLICATE_DISPLAY_NAME, INVALID_EXPERIMENT_CONFIG):
            raise HTTPException(status_code=400 if exc.code != EXPERIMENT_NOT_TERMINAL else 409, detail=exc.to_error_dict()) from exc
        raise HTTPException(status_code=400, detail=exc.to_error_dict()) from exc
