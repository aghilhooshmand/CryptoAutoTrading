# Data Model: Feature 016 — Torque bind / evaluate

## Entities

### TorquePhenotypeSource

| Field | Type | Notes |
|-------|------|--------|
| source | string | Raw Torque program text |

Validation: non-empty; must pass `torque.check` before bind.

### BoundProgram

In-memory only (not persisted in MVP).

| Field | Type | Notes |
|-------|------|--------|
| source | string | Original phenotype |
| root | BoundNode | Strategy leaf or composition |

### BoundNode

Discriminated:

1. **Leaf** — `kind=leaf`, `strategy_id`, `params` (validated ParamDef map),
   `strategy: Strategy`
2. **Compose** — `kind=compose`, `op` ∈ {`and`,`or`,`vote`}, `children: BoundNode[]`
   (min 2 children for MVP)

### CompositeStrategy

Implements `Strategy` protocol:

- `evaluate(closes)` → combine child signals per R5
- `min_history_candles()` → max of children

### TorqueEvaluateRequest (logical)

| Field | Type | Notes |
|-------|------|--------|
| phenotype | string | Torque source |
| candles | CandleClose[] or fixture id | Historical bars |
| startingCapital | decimal string | Backtest capital |
| feeRate / slippageRate | decimal string | Cost-aware |
| symbol / timeframe | string | Provenance / journals if required by engine |

### TorqueEvaluateResult

| Field | Type | Notes |
|-------|------|--------|
| ok | bool | False on form/bind/evaluate failure |
| error.code / message | string | When not ok |
| phenotype | string | Echo |
| metrics.netProfit | string | Primary |
| metrics.totalReturn | string | Optional |
| metrics.tradeCount | int | Optional |
| metrics.buyAndHoldNetProfit | string | Optional (helps 019 fitness) |
| effectiveLeaves | list | strategy ids + params used |

## Relationships

```text
TorquePhenotypeSource
    --check--> Program (FORGE)
    --bind--> BoundProgram / CompositeStrategy
    --evaluate--> Backtest run_engine
    --metrics--> TorqueEvaluateResult
```

## State transitions

N/A — request/response evaluate. No session state machine in 016.

## Invariants

1. No RealExecutionAdapter calls from bind/evaluate.
2. Unknown leaf or bad params → fail closed; no partial fill invention.
3. Same phenotype + same candles + same costs → same metrics (SC-003).
