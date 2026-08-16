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


def true_range(high: Decimal, low: Decimal, prev_close: Decimal | None) -> Decimal:
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr_series(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int,
) -> list[Decimal | None]:
    """Wilder ATR; first value at index ``period`` (after ``period`` TRs)."""
    n = len(closes)
    if period < 1 or n < period + 1 or len(highs) != n or len(lows) != n:
        return [None] * n
    out: list[Decimal | None] = [None] * n
    trs: list[Decimal] = []
    for i in range(n):
        prev = closes[i - 1] if i > 0 else None
        trs.append(true_range(highs[i], lows[i], prev))
    # Seed at index period-1 using SMA of first `period` TRs (indices 0..period-1)
    seed = sum(trs[:period], Decimal("0")) / Decimal(period)
    out[period - 1] = quantize_money(seed)
    prev_atr = out[period - 1]
    assert prev_atr is not None
    p = Decimal(period)
    for i in range(period, n):
        prev_atr = quantize_money((prev_atr * (p - Decimal("1")) + trs[i]) / p)
        out[i] = prev_atr
    return out


def stochastic_k_series(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int,
) -> list[Decimal | None]:
    """Raw %%K stochastic; None until index ``period - 1``."""
    n = len(closes)
    if period < 2 or n < period or len(highs) != n or len(lows) != n:
        return [None] * n
    out: list[Decimal | None] = [None] * n
    for i in range(period - 1, n):
        window_h = highs[i - period + 1 : i + 1]
        window_l = lows[i - period + 1 : i + 1]
        hh = max(window_h)
        ll = min(window_l)
        span = hh - ll
        if span == 0:
            out[i] = Decimal("50")
        else:
            out[i] = quantize_money((closes[i] - ll) / span * Decimal("100"))
    return out
