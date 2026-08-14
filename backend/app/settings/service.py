"""
Operator Settings service (Feature 008).

Invariant: this module only validates and persists OperatorDefaults.
It MUST NOT create, start, stop, or mutate simulation sessions, backtest runs,
or strategy comparisons (FR-005 / FR-008).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.market_data.models import ALLOWED_INTERVALS
from app.settings import repository as repo
from app.settings.starters import product_starter_defaults
from app.simulation.money import as_str, d
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, validate_and_materialize
from app.strategy.serialize import loads_params


class SettingsError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_capital(starting: Decimal, allocated: Decimal, max_pos: Decimal) -> None:
    if not (Decimal("0") < max_pos <= allocated <= starting):
        raise SettingsError(
            "invalid_config",
            "Require 0 < max_position_size <= allocated_capital <= starting_capital",
        )


def _optional_rate(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    value = d(raw)
    if value <= 0:
        raise SettingsError("invalid_config", "Optional rates must be > 0 when set")
    return as_str(value)


def _optional_weight(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    value = d(raw)
    if not (Decimal("0") < value <= Decimal("1")):
        raise SettingsError("invalid_config", "perSymbolMaxWeight must be > 0 and ≤ 1 when set")
    return as_str(value)


def _optional_allocation_id(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _optional_max_trades(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    value = int(raw)
    if value < 1:
        raise SettingsError("invalid_config", "maxTrades must be >= 1 when set")
    return value


def _validate_body(body: dict[str, Any]) -> dict[str, Any]:
    try:
        starting = d(body["startingCapital"])
        allocated_raw = body.get("allocatedCapital")
        if allocated_raw is None or allocated_raw == "":
            allocated_raw = body["startingCapital"]
        allocated = d(allocated_raw)
        max_pos = d(body["maxPositionSize"])
        fee_rate = d(body["feeRate"])
        slip_rate = d(body["slippageRate"])
    except (KeyError, ValueError, TypeError) as exc:
        raise SettingsError("invalid_config", f"Invalid configuration: {exc}") from exc

    if fee_rate < 0 or slip_rate < 0:
        raise SettingsError("invalid_config", "feeRate and slippageRate must be >= 0")

    _validate_capital(starting, allocated, max_pos)

    symbol = str(body["symbol"]).strip()
    timeframe = str(body["timeframe"]).strip()
    if not symbol:
        raise SettingsError("invalid_config", "symbol is required")
    if timeframe not in ALLOWED_INTERVALS:
        raise SettingsError(
            "invalid_config",
            "timeframe must be one of: 1m, 5m, 15m, 1h, 4h, 1d",
        )

    try:
        target = _optional_rate(body.get("targetNetProfitRate"))
        loss = _optional_rate(body.get("maxSessionLossRate"))
        max_trades = _optional_max_trades(body.get("maxTrades"))
        portfolio_max_loss_rate = _optional_rate(body.get("portfolioMaxLossRate"))
        portfolio_max_loss_amount = _optional_rate(body.get("portfolioMaxLossAmount"))
        per_symbol_max_weight = _optional_weight(body.get("perSymbolMaxWeight"))
        preferred_allocation_id = _optional_allocation_id(body.get("preferredAllocationId"))
    except (ValueError, TypeError) as exc:
        raise SettingsError("invalid_config", f"Invalid optional risk fields: {exc}") from exc

    try:
        canonical_id, effective_params, _instance = validate_and_materialize(
            body.get("strategyId"),
            body.get("strategyParams"),
        )
    except UnknownStrategyError as exc:
        raise SettingsError(exc.code, exc.message, 400) from exc
    except StrategyParamError as exc:
        raise SettingsError(exc.code, exc.message, 400) from exc

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "starting_capital": as_str(starting),
        "allocated_capital": as_str(allocated),
        "max_position_size": as_str(max_pos),
        "fee_rate": as_str(fee_rate),
        "slippage_rate": as_str(slip_rate),
        "target_net_profit_rate": target,
        "max_session_loss_rate": loss,
        "max_trades": max_trades,
        "strategy_id": canonical_id,
        "strategy_params": effective_params,
        "portfolio_max_loss_rate": portfolio_max_loss_rate,
        "portfolio_max_loss_amount": portfolio_max_loss_amount,
        "per_symbol_max_weight": per_symbol_max_weight,
        "preferred_allocation_id": preferred_allocation_id,
    }


def _payload(
    *,
    symbol: str,
    timeframe: str,
    starting_capital: str,
    allocated_capital: str,
    max_position_size: str,
    fee_rate: str,
    slippage_rate: str,
    target_net_profit_rate: str | None,
    max_session_loss_rate: str | None,
    max_trades: int | None,
    strategy_id: str,
    strategy_params: dict[str, Any],
    portfolio_max_loss_rate: str | None = None,
    portfolio_max_loss_amount: str | None = None,
    per_symbol_max_weight: str | None = None,
    preferred_allocation_id: str | None = None,
    source: str,
    updated_at: str | None,
    warning: str | None = None,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "startingCapital": starting_capital,
        "allocatedCapital": allocated_capital,
        "maxPositionSize": max_position_size,
        "feeRate": fee_rate,
        "slippageRate": slippage_rate,
        "targetNetProfitRate": target_net_profit_rate,
        "maxSessionLossRate": max_session_loss_rate,
        "maxTrades": max_trades,
        "strategyId": strategy_id,
        "strategyParams": strategy_params,
        "portfolioMaxLossRate": portfolio_max_loss_rate,
        "portfolioMaxLossAmount": portfolio_max_loss_amount,
        "perSymbolMaxWeight": per_symbol_max_weight,
        "preferredAllocationId": preferred_allocation_id,
        "updatedAt": updated_at,
        "source": source,
        "warning": warning,
    }


def _starters_response(*, warning: str | None = None) -> dict[str, Any]:
    body = product_starter_defaults()
    return _payload(
        symbol=body["symbol"],
        timeframe=body["timeframe"],
        starting_capital=body["startingCapital"],
        allocated_capital=body["allocatedCapital"],
        max_position_size=body["maxPositionSize"],
        fee_rate=body["feeRate"],
        slippage_rate=body["slippageRate"],
        target_net_profit_rate=body["targetNetProfitRate"],
        max_session_loss_rate=body["maxSessionLossRate"],
        max_trades=body["maxTrades"],
        strategy_id=body["strategyId"],
        strategy_params=dict(body["strategyParams"]),
        portfolio_max_loss_rate=body.get("portfolioMaxLossRate"),
        portfolio_max_loss_amount=body.get("portfolioMaxLossAmount"),
        per_symbol_max_weight=body.get("perSymbolMaxWeight"),
        preferred_allocation_id=body.get("preferredAllocationId"),
        source="starters",
        updated_at=None,
        warning=warning,
    )


def _validated_to_payload(validated: dict[str, Any], *, source: str, updated_at: str | None) -> dict[str, Any]:
    return _payload(
        symbol=validated["symbol"],
        timeframe=validated["timeframe"],
        starting_capital=validated["starting_capital"],
        allocated_capital=validated["allocated_capital"],
        max_position_size=validated["max_position_size"],
        fee_rate=validated["fee_rate"],
        slippage_rate=validated["slippage_rate"],
        target_net_profit_rate=validated["target_net_profit_rate"],
        max_session_loss_rate=validated["max_session_loss_rate"],
        max_trades=validated["max_trades"],
        strategy_id=validated["strategy_id"],
        strategy_params=dict(validated["strategy_params"]),
        portfolio_max_loss_rate=validated.get("portfolio_max_loss_rate"),
        portfolio_max_loss_amount=validated.get("portfolio_max_loss_amount"),
        per_symbol_max_weight=validated.get("per_symbol_max_weight"),
        preferred_allocation_id=validated.get("preferred_allocation_id"),
        source=source,
        updated_at=updated_at,
        warning=None,
    )


def _validate_stored_row(row: Any) -> dict[str, Any]:
    params = loads_params(row.strategy_params)
    return _validate_body(
        {
            "symbol": row.symbol,
            "timeframe": row.timeframe,
            "startingCapital": row.starting_capital,
            "allocatedCapital": row.allocated_capital,
            "maxPositionSize": row.max_position_size,
            "feeRate": row.fee_rate,
            "slippageRate": row.slippage_rate,
            "targetNetProfitRate": row.target_net_profit_rate,
            "maxSessionLossRate": row.max_session_loss_rate,
            "maxTrades": row.max_trades,
            "strategyId": row.strategy_id,
            "strategyParams": params,
            "portfolioMaxLossRate": getattr(row, "portfolio_max_loss_rate", None),
            "portfolioMaxLossAmount": getattr(row, "portfolio_max_loss_amount", None),
            "perSymbolMaxWeight": getattr(row, "per_symbol_max_weight", None),
            "preferredAllocationId": getattr(row, "preferred_allocation_id", None),
        }
    )


def get_settings(db: Session) -> dict[str, Any]:
    """Return effective Settings. Never mutates storage. Never starts trading."""
    row = repo.get_row(db)
    if row is None:
        return _starters_response()
    try:
        validated = _validate_stored_row(row)
    except SettingsError as exc:
        return _starters_response(
            warning=f"Saved Settings could not be used ({exc.message}). Showing product starters."
        )
    except Exception as exc:  # pragma: no cover - defensive
        return _starters_response(
            warning=f"Saved Settings could not be used ({exc}). Showing product starters."
        )
    return _validated_to_payload(validated, source="saved", updated_at=_iso(row.updated_at))


def put_settings(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    """Explicit Save. Invalid input leaves the last good row unchanged."""
    validated = _validate_body(body)
    row = repo.upsert_row(
        db,
        symbol=validated["symbol"],
        timeframe=validated["timeframe"],
        starting_capital=validated["starting_capital"],
        allocated_capital=validated["allocated_capital"],
        max_position_size=validated["max_position_size"],
        fee_rate=validated["fee_rate"],
        slippage_rate=validated["slippage_rate"],
        target_net_profit_rate=validated["target_net_profit_rate"],
        max_session_loss_rate=validated["max_session_loss_rate"],
        max_trades=validated["max_trades"],
        strategy_id=validated["strategy_id"],
        strategy_params=validated["strategy_params"],
        portfolio_max_loss_rate=validated.get("portfolio_max_loss_rate"),
        portfolio_max_loss_amount=validated.get("portfolio_max_loss_amount"),
        per_symbol_max_weight=validated.get("per_symbol_max_weight"),
        preferred_allocation_id=validated.get("preferred_allocation_id"),
    )
    return _validated_to_payload(validated, source="saved", updated_at=_iso(row.updated_at))


def reset_settings(db: Session) -> dict[str, Any]:
    """Persist product starters as active Settings. No trading side effects."""
    return put_settings(db, product_starter_defaults())
