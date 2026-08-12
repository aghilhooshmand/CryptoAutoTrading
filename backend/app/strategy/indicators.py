"""Shared Decimal indicator helpers for registered strategies."""

from __future__ import annotations

from decimal import Decimal

from app.simulation.money import quantize_money


def ema_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    """EMA with SMA seed — matches Dual EMA ``_ema`` semantics."""
    if len(values) < period:
        return [None] * len(values)
    out: list[Decimal | None] = [None] * len(values)
    seed = sum(values[:period], Decimal("0")) / Decimal(period)
    out[period - 1] = quantize_money(seed)
    k = Decimal("2") / (Decimal(period) + Decimal("1"))
    prev = out[period - 1]
    assert prev is not None
    for i in range(period, len(values)):
        prev = quantize_money(values[i] * k + prev * (Decimal("1") - k))
        out[i] = prev
    return out


def sma_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    if period < 1 or len(values) < period:
        return [None] * len(values)
    out: list[Decimal | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        out[i] = quantize_money(sum(window, Decimal("0")) / Decimal(period))
    return out


def _sqrt_decimal(value: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")
    x = value
    for _ in range(48):
        x = (x + value / x) / 2
    return quantize_money(x)


def population_stdev_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    if period < 2 or len(values) < period:
        return [None] * len(values)
    out: list[Decimal | None] = [None] * len(values)
    p = Decimal(period)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = sum(window, Decimal("0")) / p
        var = sum((x - mean) ** 2 for x in window) / p
        out[i] = _sqrt_decimal(var)
    return out


def wilder_rsi_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    """Wilder's RSI; None until index ``period`` (first RSI value)."""
    n = len(values)
    if n < period + 1 or period < 2:
        return [None] * n
    out: list[Decimal | None] = [None] * n
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, Decimal("0")))
        losses.append(max(-delta, Decimal("0")))
    avg_gain = sum(gains, Decimal("0")) / Decimal(period)
    avg_loss = sum(losses, Decimal("0")) / Decimal(period)
    out[period] = _rsi_from_avgs(avg_gain, avg_loss)
    p_dec = Decimal(period)
    for i in range(period + 1, n):
        delta = values[i] - values[i - 1]
        gain = max(delta, Decimal("0"))
        loss = max(-delta, Decimal("0"))
        avg_gain = (avg_gain * (p_dec - Decimal("1")) + gain) / p_dec
        avg_loss = (avg_loss * (p_dec - Decimal("1")) + loss) / p_dec
        out[i] = _rsi_from_avgs(avg_gain, avg_loss)
    return out


def _rsi_from_avgs(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
    if avg_loss == 0:
        return Decimal("100") if avg_gain > 0 else Decimal("50")
    rs = avg_gain / avg_loss
    return quantize_money(Decimal("100") - (Decimal("100") / (Decimal("1") + rs)))
