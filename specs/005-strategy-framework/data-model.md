# Data Model: Strategy Framework and Selection

**Feature**: `005-strategy-framework`  
**Date**: 2026-08-11  
**Related**: [spec.md](./spec.md), [research.md](./research.md), Features 003/004 session & run models

## Overview

This feature does not introduce a separate “strategy table.” Strategies are
**code-registered**. Persistence stores the **chosen canonical id** and
**effective parameters** on existing Simulation Session and Backtest Run rows.

```text
StrategyDefinition (registry, in-process)
        │
        │ resolve / validate
        ▼
SimulationSession ── strategy_id + strategy_params
BacktestRun        ── strategy_id + strategy_params
```

---

## Entity: StrategyDefinition (registry entry, not a DB row)

| Attribute | Type | Description |
|-----------|------|-------------|
| `strategy_id` | string | Canonical id (e.g. `dual_ema`) |
| `display_name` | string | Operator-facing name (e.g. “Dual EMA”) |
| `aliases` | string[] | Accepted input ids (e.g. `dual_ema_9_21`) |
| `parameters` | ParamDef[] | Declared parameters |
| `factory` | (params) → Strategy | Builds evaluate instance |

### ParamDef

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | string | API/JSON key (camelCase in HTTP, e.g. `fastPeriod`) |
| `type` | enum | `integer` \| `decimal_string` \| `string` (v1 Dual EMA uses integer) |
| `label` | string | UI label |
| `default` | value | Applied when omitted |
| `required` | bool | If true and no default → must be supplied |
| `constraints` | object | e.g. `minimum`, `maximum`, cross-field rules |

### Dual EMA registration

| Field | Value |
|-------|-------|
| Canonical id | `dual_ema` |
| Alias | `dual_ema_9_21` |
| `fastPeriod` | integer, default `9`, minimum `1` |
| `slowPeriod` | integer, default `21`, minimum `2` |
| Cross-field | `fastPeriod < slowPeriod` — strategy-level validation message for UI/API: **“Fast period must be less than slow period.”** (No generic cross-field rule engine in Feature 005.) |
| `min_history_candles` | `slowPeriod` (`S`) |
| Warm-up | HOLD while closed-candle count `< S + 1` |

---

## Entity: StrategyParameters (effective values)

Concrete map persisted after validation/materialization.

**Dual EMA example**:

```json
{"fastPeriod": 9, "slowPeriod": 21}
```

Rules:
- Always store **effective** values (defaults filled in), never an empty object
  when Dual EMA ran with defaults.
- Integers for Dual EMA periods (not decimal strings).

---

## Entity: StrategySignal (runtime, advisory)

| Attribute | Type | Description |
|-----------|------|-------------|
| `side` | enum | `BUY` \| `SELL` \| `HOLD` only |
| `candle_open_time` | int | Closed candle open time (UTC ms) |
| `reason_code` | string? | e.g. `warmup` |
| `fast_ema` | decimal? | Dual EMA diagnostic |
| `slow_ema` | decimal? | Dual EMA diagnostic |

Must not carry execution authority. Invalid sides are rejected before control.

---

## Extensions to existing entities

### SimulationSession (Feature 003)

| Field | Change |
|-------|--------|
| `strategy_id` | Store **canonical** id after resolve (`dual_ema`). Default column value in DB may remain legacy for old rows; new creates write `dual_ema`. |
| `strategy_params` | **New** `TEXT` JSON of effective parameters. Null/empty on legacy rows → treat as Dual EMA defaults `{9,21}` on read. |

### BacktestRun (Feature 004)

| Field | Change |
|-------|--------|
| `strategy_id` | Same as session: persist canonical `dual_ema` on new creates. |
| `strategy_params` | **New** `TEXT` JSON effective parameters; same legacy read rule. |

---

## Resolution & validation (create path)

```text
1. If strategyId missing/empty → reject (invalid_config / missing_strategy)
2. Resolve alias → canonical id; unknown → reject (unknown_strategy)
3. Merge submitted strategyParams with registry defaults
4. Validate types + constraints (+ Dual EMA fast < slow)
5. Persist canonical strategy_id + effective strategy_params
6. Construct strategy instance from effective params for that session/run
```

---

## Read / inspect normalization

| Stored `strategy_id` | Response `strategyId` | Params |
|----------------------|----------------------|--------|
| `dual_ema` | `dual_ema` | parse JSON or defaults |
| `dual_ema_9_21` (alias/legacy) | Prefer `dual_ema` (normalize) | parse or defaults `{9,21}` |
| other unknown | return **as-stored** for inspection | best-effort parse; may be empty |

### Legacy / unknown `strategy_id` lifecycle

| Operation | Documented alias `dual_ema_9_21` | Unknown / unregistered id |
|-----------|----------------------------------|---------------------------|
| **READ** existing row (get/list/inspect) | Allowed — normalize display toward `dual_ema` when practical | **Allowed** — return as-stored for inspection only |
| **START / RESUME** execution (sim start, pipeline tick, backtest run continue) | Allowed — resolve alias → Dual EMA | **Forbidden** — fail safe; do not construct or evaluate a strategy |
| **NEW create** (POST session / POST backtest) | Allowed — resolve alias → persist canonical `dual_ema` | **Forbidden** — reject create (`unknown_strategy`) |

Rationale: inspection of old or corrupt rows must not become an execution path after restart. Only registry-known canonical ids and documented aliases may drive trading evaluation.

---

## Relationships

- One SimulationSession / BacktestRun → exactly one strategy choice (id + params)
- StrategyDefinition : many sessions/runs (logical; no FK to code registry)
- Strategy does not own positions, cash, or orders

---

## Validation summary

| Rule | Error intent |
|------|----------------|
| Omit `strategyId` | Reject create |
| Unknown id (not canonical or alias) | Reject create |
| Invalid / failing param constraints | Reject create |
| Dual EMA `fastPeriod >= slowPeriod` | Reject create — message: “Fast period must be less than slow period.” |
| START/RESUME with unknown stored strategy id | Fail safe — do not execute |
| Backtest closed candles `< S` | `insufficient_history` (post-accept failed row per Feature 004 rules) |

---

## Out of model (v1)

- Strategy versioning table
- Multi-strategy bindings per session
- Parameter sweep / experiment entities
- Ranking or performance leaderboard entities
