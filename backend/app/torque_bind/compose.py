"""Agreement-style signal combinators and CompositeStrategy (research R5)."""

from __future__ import annotations

from typing import Sequence

from app.strategy.base import CandleClose, SignalSide, Strategy, StrategySignal


def combine_and(sides: Sequence[SignalSide]) -> SignalSide:
    if not sides:
        return SignalSide.HOLD
    if all(s == SignalSide.BUY for s in sides):
        return SignalSide.BUY
    if all(s == SignalSide.SELL for s in sides):
        return SignalSide.SELL
    return SignalSide.HOLD


def combine_or(sides: Sequence[SignalSide]) -> SignalSide:
    """BUY if any BUY and no SELL; SELL if any SELL and no BUY; else HOLD."""
    if not sides:
        return SignalSide.HOLD
    has_buy = any(s == SignalSide.BUY for s in sides)
    has_sell = any(s == SignalSide.SELL for s in sides)
    if has_buy and has_sell:
        return SignalSide.HOLD
    if has_buy:
        return SignalSide.BUY
    if has_sell:
        return SignalSide.SELL
    return SignalSide.HOLD


def combine_vote(sides: Sequence[SignalSide]) -> SignalSide:
    """Majority of non-HOLD sides; tie / empty → HOLD."""
    active = [s for s in sides if s != SignalSide.HOLD]
    if not active:
        return SignalSide.HOLD
    buys = sum(1 for s in active if s == SignalSide.BUY)
    sells = sum(1 for s in active if s == SignalSide.SELL)
    if buys > sells:
        return SignalSide.BUY
    if sells > buys:
        return SignalSide.SELL
    return SignalSide.HOLD


_COMBINERS = {
    "and": combine_and,
    "or": combine_or,
    "vote": combine_vote,
}


def combine_sides(op: str, sides: Sequence[SignalSide]) -> SignalSide:
    fn = _COMBINERS.get(op)
    if fn is None:
        raise ValueError(f"Unknown composition op: {op}")
    return fn(sides)


class CompositeStrategy:
    """Strategy that combines child Strategy signals (agreement-style)."""

    def __init__(self, op: str, children: list[Strategy]) -> None:
        if op not in _COMBINERS:
            raise ValueError(f"Unknown composition op: {op}")
        if len(children) < 2:
            raise ValueError("CompositeStrategy requires at least 2 children")
        self.op = op
        self.children = list(children)

    def min_history_candles(self) -> int:
        return max(c.min_history_candles() for c in self.children)

    def evaluate(self, closes: Sequence[CandleClose]) -> StrategySignal:
        signals = [child.evaluate(closes) for child in self.children]
        side = combine_sides(self.op, [s.side for s in signals])
        open_time = signals[0].candle_open_time if signals else 0
        return StrategySignal(
            side,
            open_time,
            None,
            None,
            f"compose_{self.op}",
        )
