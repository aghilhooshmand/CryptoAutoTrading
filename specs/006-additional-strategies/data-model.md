# Data Model: Additional Strategies

**Feature**: `006-additional-strategies`  
**Date**: 2026-08-12  
**Related**: [spec.md](./spec.md), [research.md](./research.md), Feature 005 data-model

## Overview

No new persistence entities. Strategies remain **code-registered**. Existing
Simulation Session and Backtest Run rows continue to store `strategy_id` +
`strategy_params` (effective JSON). This feature adds four
**StrategyDefinition** registry entries and documents their parameter shapes.

```text
StrategyDefinition (registry, in-process)
  dual_ema | rsi | macd | bollinger_bands | breakout
        │
        │ resolve / validate / materialize
        ▼
SimulationSession ── strategy_id + strategy_params
BacktestRun        ── strategy_id + strategy_params
```

---

## Entity: StrategyDefinition (four new registrations)

### RSI (`rsi`)

| Field | Value |
|-------|-------|
| Display name | RSI |
| Aliases | none |
| `period` | integer, default `14`, minimum `2` |
| `overbought` | integer, default `70`, minimum `1`, maximum `99` |
| `oversold` | integer, default `30`, minimum `1`, maximum `99` |
| Cross-field | `oversold < overbought` — message: “Oversold threshold must be less than overbought threshold.” |
| `min_history_candles` (`S`) | `period` |
| Warm-up | HOLD while closed-candle count &lt; `S + 1` |
| Signal | Recovery crossover out of oversold (BUY) / overbought (SELL) |

Effective params example:

```json
{"period": 14, "overbought": 70, "oversold": 30}
```

### MACD (`macd`)

| Field | Value |
|-------|-------|
| Display name | MACD |
| Aliases | none |
| `fastPeriod` | integer, default `12`, minimum `1` |
| `slowPeriod` | integer, default `26`, minimum `2` |
| `signalPeriod` | integer, default `9`, minimum `1` |
| Cross-field | `fastPeriod < slowPeriod` — message: “Fast period must be less than slow period.” |
| `min_history_candles` (`S`) | `slowPeriod + signalPeriod` |
| Warm-up | HOLD while count &lt; `S + 1` |
| Signal | MACD line / signal line crossover |

Effective params example:

```json
{"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}
```

### Bollinger Bands (`bollinger_bands`)

| Field | Value |
|-------|-------|
| Display name | Bollinger Bands |
| Aliases | none |
| `period` | integer, default `20`, minimum `2` |
| `stdDev` | `decimal_string`, default `"2.0"`, must be &gt; 0 |
| Cross-field | none |
| `min_history_candles` (`S`) | `period` |
| Warm-up | HOLD while count &lt; `S + 1` |
| Signal | Recovery crossover through lower (BUY) / upper (SELL) band |

Effective params example:

```json
{"period": 20, "stdDev": "2.0"}
```

### Breakout (`breakout`)

| Field | Value |
|-------|-------|
| Display name | Breakout |
| Aliases | none |
| `lookback` | integer, default `20`, minimum `2` |
| Cross-field | none |
| `min_history_candles` (`S`) | `lookback` |
| Warm-up | HOLD while count &lt; `S + 1` |
| Signal | Every new extreme vs prior lookback closes |

Effective params example:

```json
{"lookback": 20}
```

---

## History contract (all four + Dual EMA)

| Condition | Behavior |
|-----------|----------|
| Backtest closed candles &lt; `S` | Reject `insufficient_history` |
| Count = `S` (and until `S+1`) | Accept window; strategy emits HOLD |
| Count ≥ `S+1` | May emit BUY/SELL/HOLD per strategy rules |

---

## Unchanged entities

- **StrategySignal**: `BUY` \| `SELL` \| `HOLD` only; advisory
- **SimulationSession / BacktestRun**: columns already include `strategy_id`,
  `strategy_params`
- **Dual EMA registration**: no field or semantic changes

## Validation rules (summary)

| Strategy | Bounds | Extra |
|----------|--------|-------|
| RSI | period ≥ 2; 1 ≤ oversold, overbought ≤ 99 | oversold &lt; overbought |
| MACD | fast ≥ 1; slow ≥ 2; signal ≥ 1 | fast &lt; slow |
| Bollinger | period ≥ 2; stdDev &gt; 0 | — |
| Breakout | lookback ≥ 2 | — |

Invalid → create rejected with clear constraint message (same Feature 005
error style: e.g. `invalid_strategy_params`).
