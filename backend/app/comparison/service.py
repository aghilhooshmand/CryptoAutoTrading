"""Sync comparison orchestrator: one candle fetch, 2–5 Feature 004 legs."""

from __future__ import annotations

import json
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.backtest import repository as backtest_repo
from app.backtest import service as backtest_svc
from app.backtest.limits import is_insufficient_count, is_oversized_count
from app.comparison import repository as repo
from app.comparison.metrics import leg_metrics_from_summary
from app.db.models import StrategyComparisonRow
from app.market_data.identity import identity_api_from_row, resolve_product_identity
from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.service import bound_service_for_identity, get_market_data_service
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, validate_and_materialize
from app.strategy.serialize import display_strategy_id, dumps_params, effective_params_for_row

MIN_LEGS = 2
MAX_LEGS = 5

# Comparison-level in-flight lock (research Decision 3). Non-blocking acquire → 409.
_comparison_lock = threading.Lock()


class ComparisonError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def comparison_lock_held() -> bool:
    return _comparison_lock.locked()


def _shared_fields_from_body(body: dict[str, Any]) -> dict[str, Any]:
    """Validate shared window/money via Feature 004 validator with a placeholder strategy."""
    probe = dict(body)
    probe.pop("legs", None)
    probe.setdefault("strategyId", "dual_ema")
    probe.setdefault("strategyParams", None)
    try:
        fields = backtest_svc.validate_config(probe)
    except backtest_svc.BacktestError as exc:
        raise ComparisonError(exc.code, exc.message, exc.http_status) from exc
    fields.pop("min_history_candles", None)
    fields.pop("strategy_params_obj", None)
    fields.pop("strategy_id", None)
    fields.pop("strategy_params", None)
    fields.pop("take_profit_percent", None)
    fields.pop("stop_loss_percent", None)
    return fields


def _validate_legs(legs_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(legs_raw, list):
        raise ComparisonError("invalid_comparison", "legs must be an array")
    if not (MIN_LEGS <= len(legs_raw) <= MAX_LEGS):
        raise ComparisonError(
            "invalid_comparison",
            f"A comparison requires {MIN_LEGS}–{MAX_LEGS} legs",
        )
    prepared: list[dict[str, Any]] = []
    for i, leg in enumerate(legs_raw):
        if not isinstance(leg, dict):
            raise ComparisonError("invalid_comparison", f"leg[{i}] must be an object")
        try:
            canonical_id, effective_params, instance = validate_and_materialize(
                leg.get("strategyId"),
                leg.get("strategyParams"),
            )
        except UnknownStrategyError as exc:
            raise ComparisonError(exc.code, exc.message, 400) from exc
        except StrategyParamError as exc:
            raise ComparisonError(exc.code, exc.message, 400) from exc
        prepared.append(
            {
                "ordinal": i,
                "strategy_id": canonical_id,
                "strategy_params": dumps_params(effective_params),
                "strategy_params_obj": effective_params,
                "min_history_candles": instance.min_history_candles(),
            }
        )
    return prepared


def validate_create_body(body: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    shared = _shared_fields_from_body(body)
    legs = _validate_legs(body.get("legs"))
    return shared, legs


def comparison_to_dict(db: Session, row: StrategyComparisonRow) -> dict[str, Any]:
    legs_out: list[dict[str, Any]] = []
    for leg in repo.list_legs(db, row.id):
        metrics: dict[str, Any] = {}
        if leg.metrics_json:
            metrics = json.loads(leg.metrics_json)
        legs_out.append(
            {
                "ordinal": leg.ordinal,
                "strategyId": display_strategy_id(leg.strategy_id),
                "strategyParams": effective_params_for_row(
                    leg.strategy_id, leg.strategy_params
                ),
                "backtestRunId": leg.backtest_run_id,
                "netPnl": metrics.get("netPnl"),
                "returnPct": metrics.get("returnPct"),
                "maxDrawdown": metrics.get("maxDrawdown"),
                "maxDrawdownPct": metrics.get("maxDrawdownPct"),
                "winRate": metrics.get("winRate"),
                "roundTripCount": metrics.get("roundTripCount"),
                "fillCount": metrics.get("fillCount"),
                "totalFees": metrics.get("totalFees"),
                "totalSlippage": metrics.get("totalSlippage"),
                "bestTrade": metrics.get("bestTrade"),
                "worstTrade": metrics.get("worstTrade"),
                "buyAndHoldReturnPct": metrics.get("buyAndHoldReturnPct"),
                "vsBuyAndHoldReturnPct": metrics.get("vsBuyAndHoldReturnPct"),
            }
        )
    return {
        "id": row.id,
        "status": row.status,
        **identity_api_from_row(row),
        "timeframe": row.timeframe,
        "startTime": row.start_time,
        "endTime": row.end_time,
        "startingCapital": row.starting_capital,
        "allocatedCapital": row.allocated_capital,
        "maxPositionSize": row.max_position_size,
        "targetNetProfitRate": row.target_net_profit_rate,
        "maxSessionLossRate": row.max_session_loss_rate,
        "maxTrades": row.max_trades,
        "feeRate": row.fee_rate,
        "slippageRate": row.slippage_rate,
        "candleCount": row.candle_count,
        "buyAndHoldReturnPct": row.buy_and_hold_return_pct,
        "buyAndHoldNetPnl": row.buy_and_hold_net_pnl,
        "errorCode": row.error_code,
        "errorMessage": row.error_message,
        "createdAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
        "completedAt": (
            row.completed_at.isoformat().replace("+00:00", "Z") if row.completed_at else None
        ),
        "legs": legs_out,
    }


async def create_and_run(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    # Pre-accept validation (no durable row on failure).
    shared, legs = validate_create_body(body)
    strictest_s = max(int(leg["min_history_candles"]) for leg in legs)

    if not _comparison_lock.acquire(blocking=False):
        raise ComparisonError(
            "comparison_already_running",
            "Another comparison is already in flight",
            409,
        )
    if repo.has_running_comparison(db):
        _comparison_lock.release()
        raise ComparisonError(
            "comparison_already_running",
            "Another comparison is already in flight",
            409,
        )
    if backtest_repo.has_running(db):
        _comparison_lock.release()
        raise ComparisonError(
            "backtest_already_running",
            "A backtest is running; wait before starting a comparison",
            409,
        )

    try:
        comparison = repo.create_running(db, shared)
        for leg in legs:
            repo.add_leg(
                db,
                comparison_id=comparison.id,
                ordinal=leg["ordinal"],
                strategy_id=leg["strategy_id"],
                strategy_params=leg["strategy_params"],
            )

        try:
            ident = resolve_product_identity(shared)
            service, key = bound_service_for_identity(ident, injected=get_market_data_service())
            series = await service.get_candles(
                key,
                shared["timeframe"],
                limit=5000,
                start_time=shared["start_time"],
                end_time=shared["end_time"],
            )
        except UnsupportedSymbolError as exc:
            repo.mark_failed(db, comparison, code="unsupported_symbol", message=str(exc))
            return comparison_to_dict(db, comparison)
        except MarketDataAdapterError as exc:
            repo.mark_failed(db, comparison, code="market_data_unavailable", message=str(exc))
            return comparison_to_dict(db, comparison)
        except Exception as exc:  # noqa: BLE001
            repo.mark_failed(db, comparison, code="market_data_unavailable", message=str(exc))
            return comparison_to_dict(db, comparison)

        candles = list(series.candles)
        if is_oversized_count(len(candles)):
            repo.mark_failed(
                db,
                comparison,
                code="oversized_history",
                message="Fetched candle count exceeds maximum of 5000",
                candle_count=len(candles),
            )
            return comparison_to_dict(db, comparison)

        if is_insufficient_count(len(candles), strictest_s):
            repo.mark_failed(
                db,
                comparison,
                code="insufficient_history",
                message=(
                    f"Need at least {strictest_s} closed candles for the strictest "
                    "selected strategy (empty or too short)"
                ),
                candle_count=len(candles),
            )
            return comparison_to_dict(db, comparison)

        try:
            shared_bh_return: str | None = None
            shared_bh_pnl: str | None = None
            persisted_legs = repo.list_legs(db, comparison.id)
            for leg_meta, leg_row in zip(legs, persisted_legs, strict=True):
                run_fields = {
                    **shared,
                    "strategy_id": leg_meta["strategy_id"],
                    "strategy_params": leg_meta["strategy_params"],
                }
                run_dict = backtest_svc.run_leg_with_prefetched_candles(
                    db,
                    fields=run_fields,
                    strategy_params_obj=leg_meta["strategy_params_obj"],
                    candles=candles,
                    origin="comparison",
                    comparison_id=comparison.id,
                    wire_shared=True,
                )
                if run_dict.get("status") != "completed":
                    raise RuntimeError(
                        run_dict.get("errorMessage")
                        or run_dict.get("errorCode")
                        or "leg_failed"
                    )
                summary = run_dict.get("summary") or {}
                if shared_bh_return is None:
                    shared_bh_return = str(summary.get("buyAndHoldReturnPct") or "0")
                    shared_bh_pnl = str(summary.get("buyAndHoldNetPnl") or "0")
                metrics = leg_metrics_from_summary(
                    summary, shared_bh_return_pct=shared_bh_return
                )
                repo.update_leg(
                    db,
                    leg_row,
                    backtest_run_id=run_dict["id"],
                    metrics=metrics,
                )

            assert shared_bh_return is not None and shared_bh_pnl is not None
            repo.mark_completed(
                db,
                comparison,
                candle_count=len(candles),
                buy_and_hold_return_pct=shared_bh_return,
                buy_and_hold_net_pnl=shared_bh_pnl,
            )
        except Exception as exc:  # noqa: BLE001 — fail-closed after accept
            repo.mark_failed(
                db,
                comparison,
                code="leg_failed",
                message=str(exc) or "One or more comparison legs failed",
                candle_count=len(candles),
            )

        return comparison_to_dict(db, comparison)
    finally:
        _comparison_lock.release()


def list_comparisons_dict(db: Session, limit: int = 20) -> dict[str, Any]:
    rows = repo.list_comparisons(db, limit=limit)
    return {"comparisons": [comparison_to_dict(db, r) for r in rows]}


def get_comparison_dict(db: Session, comparison_id: str) -> dict[str, Any]:
    row = repo.get_comparison(db, comparison_id)
    if row is None:
        raise ComparisonError("comparison_not_found", "Comparison not found", 404)
    return comparison_to_dict(db, row)


def delete_comparison(db: Session, comparison_id: str) -> None:
    try:
        ok = repo.delete_comparison(db, comparison_id)
    except RuntimeError as exc:
        if str(exc) == "invalid_state":
            raise ComparisonError(
                "invalid_state", "Cannot delete a running comparison", 409
            ) from exc
        raise
    if not ok:
        raise ComparisonError("comparison_not_found", "Comparison not found", 404)
