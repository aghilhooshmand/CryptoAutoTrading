"""Fill math, mark equity, and liquidation Session NET P&L."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.simulation.money import QUANTIZE_MONEY, quantize_money


@dataclass(frozen=True)
class FillQuote:
    reference_price: Decimal
    fill_price: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    cash_delta: Decimal


def buy_fill(
    qty: Decimal,
    p_ref: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> FillQuote:
    p_fill = quantize_money(p_ref * (Decimal("1") + slippage_rate))
    notional = quantize_money(qty * p_fill)
    fee = quantize_money(notional * fee_rate)
    slippage_cost = quantize_money((p_fill - p_ref) * qty)
    cash_delta = quantize_money(-(notional + fee))
    return FillQuote(p_ref, p_fill, notional, fee, slippage_cost, cash_delta)


def sell_fill(
    qty: Decimal,
    p_ref: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> FillQuote:
    p_fill = quantize_money(p_ref * (Decimal("1") - slippage_rate))
    notional = quantize_money(qty * p_fill)
    fee = quantize_money(notional * fee_rate)
    slippage_cost = quantize_money((p_ref - p_fill) * qty)
    cash_delta = quantize_money(notional - fee)
    return FillQuote(p_ref, p_fill, notional, fee, slippage_cost, cash_delta)


def mark_equity(cash: Decimal, qty: Decimal, p_mark: Decimal | None, side: str) -> Decimal | None:
    if side == "flat":
        return quantize_money(cash)
    if p_mark is None:
        return None
    return quantize_money(cash + qty * p_mark)


def liquidation_equity(
    cash: Decimal,
    qty: Decimal,
    p_mark: Decimal | None,
    side: str,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> Decimal | None:
    if side == "flat":
        return quantize_money(cash)
    if p_mark is None:
        return None
    hyp = sell_fill(qty, p_mark, fee_rate, slippage_rate)
    return quantize_money(cash + hyp.notional - hyp.fee)


def session_net_pnl(equity: Decimal | None, start_equity: Decimal) -> Decimal | None:
    if equity is None:
        return None
    return quantize_money(equity - start_equity)


def unrealized_gross(
    qty: Decimal,
    entry_ref: Decimal | None,
    p_mark: Decimal | None,
    side: str,
) -> Decimal | None:
    if side != "long" or entry_ref is None or p_mark is None:
        return Decimal("0") if side == "flat" else None
    return quantize_money((p_mark - entry_ref) * qty)


def qty_from_notional(intended_notional: Decimal, fill_price: Decimal) -> Decimal:
    if fill_price <= 0:
        raise ValueError("fill_price must be positive")
    # Floor so notional*fee cannot exceed the cash budget implied by intended_notional.
    return (intended_notional / fill_price).quantize(QUANTIZE_MONEY, rounding=ROUND_DOWN)
