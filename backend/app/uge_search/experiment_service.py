"""Create / run Evolution experiments (Feature 020a)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.identity import resolve_product_identity
from app.market_data.service import get_market_data_service
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d
from app.uge_search import experiment_store as store
from app.uge_search.errors import (
    EXPERIMENT_NOT_FOUND,
    INVALID_EXPERIMENT_CONFIG,
    UgeSearchError,
)
from app.uge_search.experiment_runner import (
    ExperimentConflictError,
    get_experiment_runner,
)
from app.uge_search.fitness import DEFAULT_FITNESS_ID, resolve_fitness_id
from app.uge_search.grammar_builder import build_grammar
from app.uge_search.grammar_mvp import GRAMMAR_ID, load_trading_mvp_grammar
from app.uge_search.runner import run_uge_search
from app.uge_search.splits import chronological_split


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time_ms(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    # ISO-8601
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def validate_create_body(body: dict[str, Any]) -> dict[str, Any]:
    try:
        symbol = str(body.get("symbol") or "").strip()
        timeframe = str(body.get("timeframe") or "").strip()
        if not symbol or not timeframe:
            raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, "symbol and timeframe are required")
        start_time = _parse_time_ms(body["startTime"])
        end_time = _parse_time_ms(body["endTime"])
        if end_time <= start_time:
            raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, "endTime must be after startTime")
        pop = int(body.get("populationSize", 8))
        ngen = int(body.get("nGenerations", 3))
        seed = int(body.get("seed", 7))
        max_depth = int(body.get("maxDepth", 6))
        if pop < 2 or ngen < 1:
            raise UgeSearchError(
                INVALID_EXPERIMENT_CONFIG,
                "populationSize must be >= 2 and nGenerations >= 1",
            )
        train_r = float(body.get("trainRatio", 0.6))
        val_r = float(body.get("valRatio", 0.2))
        test_r = float(body.get("testRatio", 0.2))
        if abs(train_r + val_r + test_r - 1.0) > 1e-6 or min(train_r, val_r, test_r) <= 0:
            raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, "Split ratios must be > 0 and sum to 1")
        fitness_id = resolve_fitness_id(str(body.get("fitnessId") or DEFAULT_FITNESS_ID))
        capital = as_str(d(body.get("startingCapital", "1000")))
        fee = as_str(d(body.get("feeRate", DEFAULT_FEE_RATE)))
        slip = as_str(d(body.get("slippageRate", DEFAULT_SLIPPAGE_RATE)))
    except KeyError as exc:
        raise UgeSearchError(
            INVALID_EXPERIMENT_CONFIG,
            f"Missing field: {exc.args[0]}",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, str(exc)) from exc

    config: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "startTime": start_time,
        "endTime": end_time,
        "populationSize": pop,
        "nGenerations": ngen,
        "seed": seed,
        "maxDepth": max_depth,
        "fitnessId": fitness_id,
        "trainRatio": train_r,
        "valRatio": val_r,
        "testRatio": test_r,
        "startingCapital": capital,
        "feeRate": fee,
        "slippageRate": slip,
    }
    if body.get("leaves") is not None or body.get("compositionOps") is not None:
        config["leaves"] = body.get("leaves")
        config["compositionOps"] = body.get("compositionOps")
        config["paramAlternatives"] = body.get("paramAlternatives")
    return config


async def _load_candles(config: dict[str, Any]) -> list[Any]:
    from app.market_data.service import bound_service_for_identity

    ident = resolve_product_identity(
        {"symbol": config["symbol"], "timeframe": config["timeframe"]}
    )
    service, key = bound_service_for_identity(ident, injected=get_market_data_service())
    series = await service.get_candles(
        key,
        config["timeframe"],
        limit=5000,
        start_time=config["startTime"],
        end_time=config["endTime"],
    )
    return list(series.candles)


def _resolve_grammar(config: dict[str, Any]):
    if config.get("leaves") is not None or config.get("compositionOps") is not None:
        built = build_grammar(
            leaves=config.get("leaves"),
            composition_ops=config.get("compositionOps"),
            param_alternatives=config.get("paramAlternatives"),
        )
        return built.grammar, built.grammar_id
    return load_trading_mvp_grammar(), GRAMMAR_ID


def _run_job(experiment_id: str, config: dict[str, Any], candles: list[Any]) -> None:
    runner = get_experiment_runner()
    store.update_meta(
        experiment_id,
        {"status": "running", "startedAt": _now()},
    )
    grammar, grammar_id = _resolve_grammar(config)
    store.update_meta(experiment_id, {"grammarId": grammar_id})

    def on_generation(snap: dict[str, Any]) -> None:
        store.append_generation(experiment_id, snap)
        gens = store.read_generations(experiment_id)
        patch: dict[str, Any] = {"generationCount": len(gens)}
        if snap.get("bestPhenotype"):
            patch["bestPhenotype"] = snap["bestPhenotype"]
        if snap.get("fitnessMax") is not None:
            patch["trainFitness"] = snap["fitnessMax"]
        store.update_meta(experiment_id, patch)

    try:
        # Validate split against candle count early
        chronological_split(
            candles,
            train_ratio=float(config["trainRatio"]),
            val_ratio=float(config["valRatio"]),
            test_ratio=float(config["testRatio"]),
        )
        result = run_uge_search(
            candles,
            seed=int(config["seed"]),
            population_size=int(config["populationSize"]),
            n_generations=int(config["nGenerations"]),
            max_depth=int(config["maxDepth"]),
            fitness_id=str(config["fitnessId"]),
            starting_capital=Decimal(str(config["startingCapital"])),
            fee_rate=Decimal(str(config["feeRate"])),
            slippage_rate=Decimal(str(config["slippageRate"])),
            train_ratio=float(config["trainRatio"]),
            val_ratio=float(config["valRatio"]),
            test_ratio=float(config["testRatio"]),
            grammar=grammar,
            grammar_id=grammar_id,
            on_generation=on_generation,
            cancel_check=runner.cancel_requested,
        )
        status = "cancelled" if result.status == "cancelled" else (
            "completed" if result.status == "completed" else "failed"
        )
        if result.status == "terminated":
            status = "failed"
        store.update_meta(
            experiment_id,
            {
                "status": status,
                "finishedAt": _now(),
                "bestPhenotype": result.best_phenotype,
                "trainFitness": result.train_fitness,
                "validationFitness": result.validation_fitness,
                "testFitness": result.test_fitness,
                "terminationReason": result.termination_reason,
                "fitnessId": result.fitness_id,
                "grammarId": result.grammar_id,
                "generationCount": len(store.read_generations(experiment_id)),
            },
        )
    except Exception as exc:  # noqa: BLE001
        store.update_meta(
            experiment_id,
            {
                "status": "failed",
                "finishedAt": _now(),
                "errorMessage": str(exc),
                "terminationReason": "error",
            },
        )


async def create_experiment(body: dict[str, Any]) -> dict[str, Any]:
    config = validate_create_body(body)
    try:
        candles = await _load_candles(config)
    except UnsupportedSymbolError as exc:
        raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, str(exc)) from exc
    except MarketDataAdapterError as exc:
        raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, str(exc)) from exc
    return start_experiment_with_candles(config, candles)


def start_experiment_with_candles(
    config: dict[str, Any],
    candles: list[Any],
) -> dict[str, Any]:
    """Start after candles are loaded (API or tests)."""
    runner = get_experiment_runner()
    if runner.is_active():
        raise ExperimentConflictError()

    if len(candles) < 30:
        raise UgeSearchError(
            INVALID_EXPERIMENT_CONFIG,
            f"Need more closed candles in the window (got {len(candles)})",
        )

    _resolve_grammar(config)

    meta = store.create_experiment_meta(config=config, status="queued")
    eid = str(meta["id"])

    def target() -> None:
        _run_job(eid, config, candles)

    try:
        runner.start(eid, target)
    except ExperimentConflictError:
        store.update_meta(
            eid, {"status": "failed", "errorMessage": "conflict", "finishedAt": _now()}
        )
        raise

    store.update_meta(eid, {"status": "running", "startedAt": _now()})
    return store.read_meta(eid) or meta


def get_experiment(experiment_id: str, *, include_generations: bool = True) -> dict[str, Any] | None:
    meta = store.read_meta(experiment_id)
    if not meta:
        return None
    if include_generations:
        meta = dict(meta)
        meta["generations"] = store.read_generations(experiment_id)
    return meta


def list_experiments() -> list[dict[str, Any]]:
    return store.list_experiments()


def cancel_experiment(experiment_id: str) -> dict[str, Any]:
    meta = store.read_meta(experiment_id)
    if not meta:
        raise UgeSearchError(EXPERIMENT_NOT_FOUND, "Experiment not found")
    status = str(meta.get("status"))
    if status in ("completed", "failed", "cancelled"):
        raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, f"Experiment already terminal ({status})")
    runner = get_experiment_runner()
    if not runner.request_cancel(experiment_id):
        # Not the active thread — still mark cancelled if queued
        if status == "queued":
            store.update_meta(
                experiment_id,
                {"status": "cancelled", "finishedAt": _now(), "terminationReason": "operator_cancel"},
            )
            return store.read_meta(experiment_id) or meta
        raise UgeSearchError(INVALID_EXPERIMENT_CONFIG, "Experiment is not the active run")
    # Status flips when job finishes cancel path; optimistically note cancel requested
    store.update_meta(experiment_id, {"terminationReason": "operator_cancel_requested"})
    return store.read_meta(experiment_id) or meta
