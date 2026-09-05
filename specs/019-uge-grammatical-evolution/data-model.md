# Data Model: Feature 019 — UGE search

## Entities

### CandleSnapshot

| Field | Type | Notes |
|-------|------|--------|
| candles | Candlestick[] | Sorted by `openTime` ascending |
| symbol / timeframe | string | Provenance |
| source | string | e.g. fixture id or recorded range |

### ChronologicalSplit

| Field | Type | Notes |
|-------|------|--------|
| train | Candlestick[] | Contiguous prefix |
| validation | Candlestick[] | Middle segment |
| test | Candlestick[] | Suffix |
| trainRatio / valRatio / testRatio | float | Default 0.6 / 0.2 / 0.2; must sum to 1 |

Invariant: no shuffle; boundaries by index only.

### TradingMvpGrammar

| Field | Type | Notes |
|-------|------|--------|
| grammarId | string | e.g. `trading_mvp` |
| bnfText / path | string | Loaded into FORGE `Grammar` |
| maxDepth | int | Passed to UGE run config |

### UgeRunConfig

| Field | Type | Notes |
|-------|------|--------|
| seed | int | RNG |
| populationSize | int | |
| nGenerations | int | |
| maxDepth | int | |
| startingCapital / feeRate / slippageRate | decimal string | Forwarded to 016 evaluate |
| split | ChronologicalSplit params | |

### UgeRunResult

| Field | Type | Notes |
|-------|------|--------|
| status | string | From `RunOutcome.status` |
| bestPhenotype | string \| null | Torque source |
| trainFitness | float \| null | Objective used in search |
| validationFitness | float \| null | Post-hoc on val candles |
| testFitness | float \| null | Optional; only after freeze |
| generationSummaries | list | Optional thin log |
| artifactPath | string \| null | Persist location |

### FrozenPhenotypeArtifact (JSON)

Persisted US3 record — see research R8. Enough to re-run
`evaluate_phenotype` without UGE.

## Relationships

```text
CandleSnapshot --split--> ChronologicalSplit
UGEEngine + Grammar + train candles --run--> UgeRunResult
UgeRunResult --persist--> FrozenPhenotypeArtifact
FrozenPhenotypeArtifact --evaluate_phenotype--> metrics (no UGE)
```

## State transitions

N/A session machine. Run is request/batch: configured → running → completed |
terminated | failed.

## Invariants

1. Selection fitness uses **train** candles only.
2. Invalid mapping or 016 evaluate failure → no fitness (UGE treats as failed).
3. No RealExecutionAdapter calls.
4. Same seed + grammar + snapshot + config → same best phenotype (SC-003).
