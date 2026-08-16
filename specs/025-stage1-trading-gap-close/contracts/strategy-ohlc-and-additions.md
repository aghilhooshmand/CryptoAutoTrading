# Contract: Strategy OHLC enrichment and additions

**Feature**: `025-stage1-trading-gap-close`  
**Date**: 2026-08-16  
**Extends**: Features 005/006 strategy registry  
**Consumer**: `GET /strategies`, Simulation, Backtest, tests

---

## Candle input

Strategy `evaluate` receives bars with at least:

```text
openTime, open, high, low, close
```

Optional volume fields MAY be present; required Feature 025 strategies MUST NOT
depend on volume.

Existing strategies (`dual_ema`, `rsi`, `macd`, `bollinger_bands`, `breakout`)
MUST keep prior close-based signal behavior (no silent semantic change).

---

## `GET /strategies` — required new entries

After Feature 025, registry MUST include the original five **plus**:

1. `stochastic`
2. `keltner_channel`
3. `roc_momentum`

Exact ParamDef defaults are implementation-defined but MUST be documented in
registry metadata (integer/decimal constraints; fail closed on invalid params).

### Diversity intent

| ID | Role |
|----|------|
| `stochastic` | Range oscillator ≠ RSI |
| `keltner_channel` | ATR channel ≠ Bollinger |
| `roc_momentum` | Close momentum ≠ Dual EMA/MACD |

### Deferred

`relative_volume` (or equivalent) is **not** required for Feature 025 DONE.

---

## Unchanged

- Strategies remain advisory; Controller/Risk authoritative.
- No plugin architecture / dynamic indicator DSL.
- Create Simulation/Backtest still pass `strategyId` + `strategyParams`.
