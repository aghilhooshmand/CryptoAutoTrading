# Contract: Protective TP/SL exits

**Feature**: `025-stage1-trading-gap-close`  
**Date**: 2026-08-16  
**Consumer**: Simulation + Backtest APIs, Auto Trading UI, tests

---

## Configuration (create / start)

Optional body fields (camelCase JSON; decimal strings):

| Field | Meaning |
|-------|---------|
| `takeProfitPercent` | Fraction of entry (e.g. `"0.02"` = +2% TP). Omit/null = disabled |
| `stopLossPercent` | Fraction of entry (e.g. `"0.01"` = −1% SL). Omit/null = disabled |

Validation failures → HTTP `400` / `invalid_config` (or existing invalid config envelope).

Operator defaults MAY seed these fields; they do not rewrite running sessions.

---

## Session / run status (while long)

When `positionSide == "long"`, response SHOULD include:

| Field | Meaning |
|-------|---------|
| `entryFillPrice` | Actual entry fill price |
| `takeProfitPrice` | Derived absolute TP or null |
| `takeProfitPercent` | Configured % or null |
| `stopLossPrice` | Derived absolute SL or null |
| `stopLossPercent` | Configured % or null |

While long, clients MUST NOT offer editors that PATCH these levels (MVP).

---

## Trigger rules (both modes)

Given absolute levels set at entry:

1. Never evaluate on `entry_fill_candle_open_time`.
2. On a later closed candle: if `low <= stopLossPrice` → `stop_loss`.
3. Else if `high >= takeProfitPrice` → `take_profit`.
4. Else continue to strategy.

Session/emergency hard-stops still run first (existing).

---

## Fill rules

| Mode | Fill after protective trigger |
|------|-------------------------------|
| Simulation | Trustworthy live mark via existing Execution path |
| Backtest | Next candle open via existing next-open path; if no next candle → existing fail-closed / end rules |

**Forbidden**: using `takeProfitPrice` / `stopLossPrice` as fill price.

---

## Exit reasons

Closing protective exits MUST surface stable reasons `take_profit` or
`stop_loss` distinct from strategy and session stops.

---

## `maxTrades` / strategy-fill counting (locked)

Align with Feature 003: `maxTrades` limits **strategy-driven** fills only.

Protective TP/SL exits MUST be recorded as **non-strategy / forced-style** closes
(e.g. Simulation `is_forced=True` / equivalent Backtest forced flag) so they:

- do **not** increment `strategyFillCount`;
- do **not** consume a `maxTrades` slot;
- remain distinguishable via `take_profit` / `stop_loss` reasons.

Session hard-stops and emergency flatten retain existing behavior.
