"""Backtest service: validate, sync run, list/get/delete."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.backtest.limits import (
    assert_supported_interval,
    is_insufficient_count,
    is_oversized_count,
    is_oversized_estimate,
)
from app.db.models import BacktestRunRow
from app.execution.tpsl import validate_percents
from app.market_data.adapters.base import MarketDataAdapterError, UnsupportedSymbolError
from app.market_data.service import get_market_data_service
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, validate_and_materialize
from app.strategy.serialize import (
    display_strategy_id,
    dumps_params,
    effective_params_for_row,
)


class BacktestError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _dec(value: str, field: str) -> Decimal:
    try:
        out = d(value)
    except (InvalidOperation, ValueError) as exc:
        raise BacktestError("invalid_config", f"Invalid decimal for {field}") from exc
    return out


def validate_config(body: dict[str, Any]) -> dict[str, Any]:
    symbol = str(body.get("symbol") or "").strip()
    timeframe = str(body.get("timeframe") or "").strip()
    if not symbol:
        raise BacktestError("invalid_config", "symbol is required")
    try:
        assert_supported_interval(timeframe)
    except ValueError as exc:
        raise BacktestError("unsupported_timeframe", str(exc)) from exc

    try:
        start_time = int(body["startTime"])
        end_time = int(body["endTime"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BacktestError("invalid_config", "startTime and endTime are required integers") from exc
    if end_time <= start_time:
        raise BacktestError("invalid_config", "endTime must be greater than startTime")

    starting = _dec(str(body.get("startingCapital", "")), "startingCapital")
    allocated = _dec(
        str(body.get("allocatedCapital") or body.get("startingCapital") or ""),
        "allocatedCapital",
    )
    max_pos = _dec(str(body.get("maxPositionSize", "")), "maxPositionSize")
    if not (Decimal("0") < max_pos <= allocated <= starting):
        raise BacktestError(
            "invalid_config",
            "Require 0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital",
        )

    fee_rate = (
        _dec(str(body["feeRate"]), "feeRate")
        if body.get("feeRate") is not None
        else DEFAULT_FEE_RATE
    )
    slip_rate = (
        _dec(str(body["slippageRate"]), "slippageRate")
        if body.get("slippageRate") is not None
        else DEFAULT_SLIPPAGE_RATE
    )
    if fee_rate < 0 or slip_rate < 0:
        raise BacktestError("invalid_config", "feeRate and slippageRate must be ≥ 0")

    max_trades = body.get("maxTrades")
    if max_trades is not None:
        try:
            max_trades = int(max_trades)
        except (TypeError, ValueError) as exc:
            raise BacktestError("invalid_config", "maxTrades must be an integer") from exc
        if max_trades < 1:
            raise BacktestError("invalid_config", "maxTrades must be ≥ 1")

    profit_rate = body.get("targetNetProfitRate")
    loss_rate = body.get("maxSessionLossRate")
    profit_amt = None
    loss_amt = None
    profit_rate_s = None
    loss_rate_s = None
    if profit_rate is not None and str(profit_rate) != "":
        pr = _dec(str(profit_rate), "targetNetProfitRate")
        if pr <= 0:
            raise BacktestError("invalid_config", "targetNetProfitRate must be > 0")
        profit_rate_s = as_str(pr)
        profit_amt = as_str(allocated * pr)
    if loss_rate is not None and str(loss_rate) != "":
        lr = _dec(str(loss_rate), "maxSessionLossRate")
        if lr <= 0:
            raise BacktestError("invalid_config", "maxSessionLossRate must be > 0")
        loss_rate_s = as_str(lr)
        loss_amt = as_str(allocated * lr)

    if is_oversized_estimate(start_time, end_time, timeframe):
        raise BacktestError(
            "oversized_history",
            "Requested window exceeds maximum of 5000 candles",
        )

    try:
        canonical_id, effective_params, instance = validate_and_materialize(
            body.get("strategyId"),
            body.get("strategyParams"),
        )
    except UnknownStrategyError as exc:
        raise BacktestError(exc.code, exc.message, 400) from exc
    except StrategyParamError as exc:
        raise BacktestError(exc.code, exc.message, 400) from exc

    try:
        tp_pct, sl_pct = validate_percents(
            body.get("takeProfitPercent"),
            body.get("stopLossPercent"),
        )
    except ValueError as exc:
        raise BacktestError("invalid_config", str(exc)) from exc

    min_history = instance.min_history_candles()

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "start_time": start_time,
        "end_time": end_time,
        "starting_capital": as_str(starting),
        "allocated_capital": as_str(allocated),
        "max_position_size": as_str(max_pos),
        "target_net_profit_rate": profit_rate_s,
        "max_session_loss_rate": loss_rate_s,
        "target_net_profit_amount": profit_amt,
        "max_session_loss_amount": loss_amt,
        "max_trades": max_trades,
        "fee_rate": as_str(fee_rate),
        "slippage_rate": as_str(slip_rate),
        "strategy_id": canonical_id,
        "strategy_params": dumps_params(effective_params),
        "take_profit_percent": as_str(tp_pct) if tp_pct is not None else None,
        "stop_loss_percent": as_str(sl_pct) if sl_pct is not None else None,
        "min_history_candles": min_history,
        "strategy_params_obj": effective_params,
    }


async def create_and_run(db: Session, body: dict[str, Any], *, wire_shared: bool = True) -> dict[str, Any]:
    if repo.has_running(db):
        raise BacktestError("backtest_already_running", "Another backtest is running", 409)

    fields = validate_config(body)
    min_history = int(fields.pop("min_history_candles"))
    strategy_params_obj = fields.pop("strategy_params_obj")
    # Pre-accept oversized already checked. Create running row, then fetch.
    run = repo.create_running_run(db, fields)

    try:
        service = get_market_data_service()
        series = await service.get_candles(
            fields["symbol"],
            fields["timeframe"],
            limit=5000,
            start_time=fields["start_time"],
            end_time=fields["end_time"],
        )
    except UnsupportedSymbolError as exc:
        repo.mark_failed(db, run, code="unsupported_symbol", message=str(exc))
        return run_to_dict(db, run)
    except MarketDataAdapterError as exc:
        repo.mark_failed(db, run, code="market_data_unavailable", message=str(exc))
        return run_to_dict(db, run)
    except Exception as exc:  # noqa: BLE001
        repo.mark_failed(db, run, code="market_data_unavailable", message=str(exc))
        return run_to_dict(db, run)

    candles = list(series.candles)
    if is_oversized_count(len(candles)):
        # Spec: oversized should preferably be pre-accept; if fetch exceeds, fail the row.
        repo.mark_failed(
            db,
            run,
            code="oversized_history",
            message="Fetched candle count exceeds maximum of 5000",
        )
        return run_to_dict(db, run)

    if is_insufficient_count(len(candles), min_history):
        repo.mark_failed(
            db,
            run,
            code="insufficient_history",
            message=(
                f"Need at least {min_history} closed candles in the window "
                "(empty or too short)"
            ),
        )
        return run_to_dict(db, run)

    return complete_run_with_candles(
        db,
        run,
        candles,
        fields=fields,
        strategy_params_obj=strategy_params_obj,
        wire_shared=wire_shared,
    )


def complete_run_with_candles(
    db: Session,
    run: BacktestRunRow,
    candles: list[Any],
    *,
    fields: dict[str, Any],
    strategy_params_obj: dict[str, Any],
    wire_shared: bool = True,
) -> dict[str, Any]:
    """Run Feature 004 engine on an existing running row with prefetched candles.

    Used by comparison legs so the shared series is not re-fetched.
    """
    summary = run_engine(
        db,
        run.id,
        candles,
        starting_capital=d(fields["starting_capital"]),
        allocated_capital=d(fields["allocated_capital"]),
        max_position_size=d(fields["max_position_size"]),
        fee_rate=d(fields["fee_rate"]),
        slippage_rate=d(fields["slippage_rate"]),
        max_trades=fields["max_trades"],
        target_net_profit_amount=(
            d(fields["target_net_profit_amount"])
            if fields["target_net_profit_amount"]
            else None
        ),
        max_session_loss_amount=(
            d(fields["max_session_loss_amount"])
            if fields["max_session_loss_amount"]
            else None
        ),
        wire_shared=wire_shared,
        strategy_id=fields["strategy_id"],
        strategy_params=strategy_params_obj,
        take_profit_percent=(
            d(fields["take_profit_percent"]) if fields.get("take_profit_percent") else None
        ),
        stop_loss_percent=(
            d(fields["stop_loss_percent"]) if fields.get("stop_loss_percent") else None
        ),
    )
    repo.mark_completed(db, run, summary=summary, candle_count=len(candles))
    return run_to_dict(db, run)


def run_leg_with_prefetched_candles(
    db: Session,
    *,
    fields: dict[str, Any],
    strategy_params_obj: dict[str, Any],
    candles: list[Any],
    origin: str = "manual",
    comparison_id: str | None = None,
    wire_shared: bool = True,
) -> dict[str, Any]:
    """Create a backtest run and evaluate it on the given candle series (no fetch)."""
    run_fields = dict(fields)
    run_fields["origin"] = origin
    run_fields["comparison_id"] = comparison_id
    run = repo.create_running_run(db, run_fields)
    return complete_run_with_candles(
        db,
        run,
        candles,
        fields=run_fields,
        strategy_params_obj=strategy_params_obj,
        wire_shared=wire_shared,
    )


def run_to_dict(db: Session, run: BacktestRunRow, *, include_summary: bool = True) -> dict[str, Any]:
    summary = None
    if include_summary and run.summary_json:
        summary = json.loads(run.summary_json)
    elif include_summary and run.status == "completed":
        summary = {}
    out: dict[str, Any] = {
        "id": run.id,
        "status": run.status,
        "symbol": run.symbol,
        "timeframe": run.timeframe,
        "startTime": run.start_time,
        "endTime": run.end_time,
        "startingCapital": run.starting_capital,
        "allocatedCapital": run.allocated_capital,
        "maxPositionSize": run.max_position_size,
        "targetNetProfitRate": run.target_net_profit_rate,
        "maxSessionLossRate": run.max_session_loss_rate,
        "targetNetProfitAmount": run.target_net_profit_amount,
        "maxSessionLossAmount": run.max_session_loss_amount,
        "maxTrades": run.max_trades,
        "feeRate": run.fee_rate,
        "slippageRate": run.slippage_rate,
        "takeProfitPercent": getattr(run, "take_profit_percent", None),
        "stopLossPercent": getattr(run, "stop_loss_percent", None),
        "strategyId": display_strategy_id(run.strategy_id),
        "strategyParams": effective_params_for_row(run.strategy_id, run.strategy_params),
        "origin": getattr(run, "origin", None) or "manual",
        "comparisonId": getattr(run, "comparison_id", None),
        "candleCount": run.candle_count,
        "createdAt": run.created_at.isoformat().replace("+00:00", "Z") if run.created_at else None,
        "startedAt": run.started_at.isoformat().replace("+00:00", "Z") if run.started_at else None,
        "completedAt": (
            run.completed_at.isoformat().replace("+00:00", "Z") if run.completed_at else None
        ),
        "errorCode": run.error_code,
        "errorMessage": run.error_message,
        "summary": summary,
    }
    return out


def list_runs_dict(
    db: Session,
    limit: int = 20,
    *,
    include_comparison_origin: bool = False,
) -> dict[str, Any]:
    rows = repo.list_runs(
        db, limit=limit, include_comparison_origin=include_comparison_origin
    )
    runs = []
    for r in rows:
        item = run_to_dict(db, r)
        if item.get("summary"):
            s = item["summary"]
            item["summary"] = {
                "netPnl": s.get("netPnl"),
                "returnPct": s.get("returnPct"),
                "tradeCount": s.get("tradeCount"),
            }
        runs.append(item)
    return {"runs": runs}


def get_run_dict(db: Session, run_id: str) -> dict[str, Any]:
    row = repo.get_run(db, run_id)
    if row is None:
        raise BacktestError("run_not_found", "Backtest run not found", 404)
    return run_to_dict(db, row)


def trades_dict(db: Session, run_id: str) -> dict[str, Any]:
    if repo.get_run(db, run_id) is None:
        raise BacktestError("run_not_found", "Backtest run not found", 404)
    trades = []
    for t in repo.list_trades(db, run_id):
        trades.append(
            {
                "id": t.id,
                "side": t.side,
                "qty": t.qty,
                "referencePrice": t.reference_price,
                "fillPrice": t.fill_price,
                "fee": t.fee,
                "slippageCost": t.slippage_cost,
                "notional": t.notional,
                "signalCandleOpenTime": t.signal_candle_open_time,
                "fillCandleOpenTime": t.fill_candle_open_time,
                "isEndOfRunFlatten": t.is_end_of_run_flatten,
                "isForcedClose": t.is_forced_close,
            }
        )
    return {"trades": trades}


def decisions_dict(db: Session, run_id: str) -> dict[str, Any]:
    if repo.get_run(db, run_id) is None:
        raise BacktestError("run_not_found", "Backtest run not found", 404)
    decisions = []
    for drow in repo.list_decisions(db, run_id):
        decisions.append(
            {
                "id": drow.id,
                "candleOpenTime": drow.candle_open_time,
                "signal": drow.signal,
                "outcome": drow.outcome,
                "reasonCode": drow.reason_code,
                "reasonMessage": drow.reason_message,
                "fastEma": drow.fast_ema,
                "slowEma": drow.slow_ema,
            }
        )
    return {"decisions": decisions}


def delete_run(db: Session, run_id: str) -> None:
    try:
        ok = repo.delete_run(db, run_id)
    except RuntimeError as exc:
        if str(exc) == "invalid_state":
            raise BacktestError("invalid_state", "Cannot delete a running backtest", 409) from exc
        raise
    if not ok:
        raise BacktestError("run_not_found", "Backtest run not found", 404)
