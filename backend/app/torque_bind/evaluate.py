"""Backtest wire + evaluate_phenotype for Feature 016 / 019 fitness."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.backtest import repository as repo
from app.backtest.engine import run_engine
from app.db.models import Base
from app.market_data.models import Candlestick
from app.simulation.money import DEFAULT_FEE_RATE, DEFAULT_SLIPPAGE_RATE, as_str, d
from app.strategy.base import Strategy
from app.torque_bind.bind import (
    bind_to_program,
    collect_effective_leaves,
    ensure_strategies_registered,
)
from app.torque_bind.errors import EVALUATE_FAILED, TorqueBindError


def _ephemeral_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def run_bound_backtest(
    strategy: Strategy,
    candles: list[Candlestick],
    *,
    starting_capital: Decimal | str = Decimal("1000"),
    allocated_capital: Decimal | str | None = None,
    max_position_size: Decimal | str | None = None,
    fee_rate: Decimal | str = DEFAULT_FEE_RATE,
    slippage_rate: Decimal | str = DEFAULT_SLIPPAGE_RATE,
    max_trades: int | None = None,
    target_net_profit_amount: Decimal | None = None,
    max_session_loss_amount: Decimal | None = None,
    db: Session | None = None,
    symbol: str = "btc_usdt",
    timeframe: str = "1h",
    strategy_id_label: str = "torque_bound",
) -> dict[str, Any]:
    """
    Run Feature 004 ``run_engine`` with an already-bound Strategy.

    Returns raw engine summary (``netPnl``, ``returnPct``, …).
    """
    ensure_strategies_registered()
    if not candles:
        raise TorqueBindError(EVALUATE_FAILED, "No candles provided for Backtest")

    capital = d(starting_capital) if not isinstance(starting_capital, Decimal) else starting_capital
    alloc = (
        d(allocated_capital)
        if allocated_capital is not None
        else capital
    )
    max_pos = (
        d(max_position_size)
        if max_position_size is not None
        else capital
    )
    fee = d(fee_rate) if not isinstance(fee_rate, Decimal) else fee_rate
    slip = d(slippage_rate) if not isinstance(slippage_rate, Decimal) else slippage_rate

    own_session = db is None
    session = db if db is not None else _ephemeral_session()
    try:
        fields = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_time": candles[0].openTime,
            "end_time": candles[-1].openTime + 1,
            "starting_capital": as_str(capital),
            "allocated_capital": as_str(alloc),
            "max_position_size": as_str(max_pos),
            "target_net_profit_rate": None,
            "max_session_loss_rate": None,
            "target_net_profit_amount": None,
            "max_session_loss_amount": None,
            "max_trades": max_trades,
            "fee_rate": as_str(fee),
            "slippage_rate": as_str(slip),
            "strategy_id": strategy_id_label,
        }
        run = repo.create_running_run(session, fields)
        summary = run_engine(
            session,
            run.id,
            candles,
            starting_capital=capital,
            allocated_capital=alloc,
            max_position_size=max_pos,
            fee_rate=fee,
            slippage_rate=slip,
            max_trades=max_trades,
            target_net_profit_amount=target_net_profit_amount,
            max_session_loss_amount=max_session_loss_amount,
            wire_shared=True,
            strategy=strategy,
        )
        repo.mark_completed(session, run, summary=summary, candle_count=len(candles))
        return summary
    finally:
        if own_session:
            session.close()


def evaluate_phenotype(
    source: str,
    *,
    candles: list[Candlestick],
    starting_capital: Decimal | str = Decimal("1000"),
    allocated_capital: Decimal | str | None = None,
    max_position_size: Decimal | str | None = None,
    fee_rate: Decimal | str = DEFAULT_FEE_RATE,
    slippage_rate: Decimal | str = DEFAULT_SLIPPAGE_RATE,
    max_trades: int | None = None,
    db: Session | None = None,
    symbol: str = "btc_usdt",
    timeframe: str = "1h",
) -> dict[str, Any]:
    """
    Public evaluate envelope for Feature 019 fitness.

    Success: ``{ok, phenotype, metrics, effectiveLeaves}``.
    Failure: ``{ok: false, error: {code, message}}`` — never invents fills.
    """
    phenotype = "" if source is None else str(source).strip()
    try:
        program = bind_to_program(phenotype)
        summary = run_bound_backtest(
            program.root.strategy,
            candles,
            starting_capital=starting_capital,
            allocated_capital=allocated_capital,
            max_position_size=max_position_size,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            max_trades=max_trades,
            db=db,
            symbol=symbol,
            timeframe=timeframe,
            strategy_id_label="torque_bound",
        )
        leaves = collect_effective_leaves(program.root)
        return {
            "ok": True,
            "phenotype": phenotype,
            "metrics": {
                "netProfit": summary["netPnl"],
                "totalReturn": summary["returnPct"],
                "tradeCount": summary["tradeCount"],
                "buyAndHoldNetProfit": summary["buyAndHoldNetPnl"],
            },
            "effectiveLeaves": leaves,
        }
    except TorqueBindError as exc:
        return {"ok": False, "error": exc.to_error_dict()}
    except Exception as exc:  # noqa: BLE001 — fail closed for evaluate surface
        return {
            "ok": False,
            "error": {"code": EVALUATE_FAILED, "message": str(exc)},
        }
