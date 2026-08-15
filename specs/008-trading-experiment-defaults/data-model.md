# Data Model: Trading & Experiment Defaults

**Feature**: `008-trading-experiment-defaults`  
**Date**: 2026-08-12  
**Related**: Feature 003–007 create configs; Feature 005/006 strategy registry

## Entities

### OperatorDefaults (Settings)

Singleton local document: reusable defaults for **new** Simulation, Backtest,
and Strategy Comparison configurations. Never linked as a live FK from
historical sessions/runs/comparisons.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `symbol` | Trading pair id (e.g. `btc_usdt`) | yes |
| `timeframe` | Signal timeframe (e.g. `1h`) | yes |
| `startingCapital` | Decimal string | yes |
| `allocatedCapital` | Decimal string | yes |
| `maxPositionSize` | Decimal string | yes |
| `feeRate` | Fraction of notional (decimal string) | yes |
| `slippageRate` | Adverse-fill fraction (decimal string) | yes |
| `targetNetProfitRate` | Fraction of allocated, or unset | no |
| `maxSessionLossRate` | Fraction of allocated, or unset | no |
| `maxTrades` | Positive int, or unset | no |
| `strategyId` | Canonical registry id | yes |
| `strategyParams` | Object matching that strategy’s schema | yes |
| `decisionLogMode` | `important_only` \| `full_audit` — default for **new Simulations** only | yes (default `important_only`) |
| `updatedAt` | ISO / ms timestamp of last successful Save or Reset | yes |

**Persistence (logical)**: one SQLite row (e.g. table `operator_defaults` with
fixed primary key `1`, or equivalent singleton). Payload may be typed columns
and/or a validated JSON blob; serializers expose camelCase API fields above.

**Not stored in v1** (remain per-form):
- Simulation `durationSeconds`
- Backtest / Comparison historical `startTime` / `endTime`
- GE / experiment population knobs
- Exchange credentials, API keys, real-money flags

### ProductStarterDefaults

Built-in constant set (code, not a second editable table). Used when:

1. No row exists yet (first `GET`),
2. Stored row is corrupt / fails validation on read (fail-closed),
3. Operator confirms Reset (`POST /settings/reset` persists these values).

| Field | Starter value |
|-------|----------------|
| `symbol` | `btc_usdt` |
| `timeframe` | `1h` |
| `startingCapital` / `allocatedCapital` / `maxPositionSize` | `1000` / `1000` / `1000` |
| `feeRate` / `slippageRate` | `0.002` / `0.0005` |
| Optional risk trio | unset |
| `strategyId` / `strategyParams` | `dual_ema` + registry defaults (`fastPeriod: 9`, `slowPeriod: 21`) |
| `decisionLogMode` | `important_only` |

### Effective Configuration (existing — unchanged ownership)

Concrete config persisted on:

- Simulation Session
- Backtest Run
- Strategy Comparison (+ legs)

Copied from the create-form values at create time (which may have been
initialized from Settings then overridden). **No foreign key** to
OperatorDefaults. Later Settings edits MUST NOT mutate these rows.

### Preferred Strategy Selection

Subset of OperatorDefaults: `strategyId` + `strategyParams`. Must pass
`validate_and_materialize` (or equivalent registry validation) on Save.

## Validation rules (Save / Reset)

Align with Simulation / Backtest / Comparison create validation where fields
overlap:

1. **Capital nesting**: `0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital`
2. **Rates**: fee / slippage finite, non-negative, within the same bounds as
   create APIs (reuse existing parsers)
3. **Optional risk**: empty / null ⇒ unset (not zero). If present, must be
   valid positive fractions / ints per existing rules
4. **Strategy**: known registry id; params satisfy schema + constraints
5. **Symbol / timeframe**: same allowed sets as create forms

Invalid Save → reject; **do not** overwrite the last successfully saved row.

## State / lifecycle

```text
(no row) ──GET──► respond with ProductStarterDefaults (source=starters)
                │
                ├──PUT valid──► row exists (source=saved)
                │
                └──POST reset──► row = ProductStarterDefaults (source=saved|starters)

Corrupt row on GET ──► ProductStarterDefaults + warning (fail-closed)
```

Settings has **no** running/stopped trading states. Save and Reset MUST NOT
start, stop, or modify sessions, runs, or comparisons.

## Relationships

```text
OperatorDefaults  (singleton)
        │
        │  copy-on-fresh-form-open only (application layer)
        ▼
Create form draft ──create──► Effective Configuration
                              (Session / Run / Comparison)

ProductStarterDefaults ──used by──► GET (empty/corrupt) + Reset
```

No DB relationship from historical artifacts back to Settings.

## Read model flags (API)

| Flag | Meaning |
|------|---------|
| `source: "starters"` | Response body is product starters (no usable saved row) |
| `source: "saved"` | Response body is the persisted OperatorDefaults |
| `warning` (optional) | Human-readable note when fail-closed from corrupt storage |
