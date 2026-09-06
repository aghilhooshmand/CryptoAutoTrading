# Data Model: Evolution Experiments & Results

**Feature**: `020-evolution-experiments`  
**Date**: 2026-09-06

## 1. EvolutionExperiment

Authoritative record of one offline UGE lab run.

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | Stable id (uuid or time-based) |
| `status` | enum | `queued` \| `running` \| `completed` \| `failed` \| `cancelled` |
| `createdAt` / `startedAt` / `finishedAt` | ISO-8601 | |
| `config` | object | See ExperimentConfig |
| `grammarId` | string | e.g. `trading_mvp` or `structured_<hash>` (020b) |
| `bestPhenotype` | string \| null | Set when known (end, or last gen) |
| `trainFitness` | number \| null | Selection fitness of best |
| `validationFitness` | number \| null | Report-only after terminal success path |
| `testFitness` | number \| null | Optional; never used for selection |
| `fitnessId` | string | Allow-list id from 019 |
| `terminationReason` | string \| null | From UGE / cancel / error |
| `errorMessage` | string \| null | Fail-closed detail |
| `generationCount` | int | Snapshots received |

### ExperimentConfig (embedded)

| Field | Notes |
|-------|--------|
| `symbol`, `timeframe`, `startTime`, `endTime` | Candle window |
| `populationSize`, `nGenerations`, `seed`, `maxDepth` | UGE |
| `fitnessId` | Allow-list |
| `trainRatio`, `valRatio`, `testRatio` | Chronological split |
| `startingCapital`, `feeRate`, `slippageRate` | Evaluate economics |
| `leaves`, `compositionOps`, `paramAlternatives` | **020b only**; ignored/default in 020a |

### Status transitions

```text
queued → running → completed
                 → failed
                 → cancelled
```

- Only one experiment in `queued`/`running` at a time (deployment-wide).
- Cancel from `running` → `cancelled` at generation boundary.
- Freeze (020c) allowed only from `completed` | `failed` | `cancelled` when
  `bestPhenotype` is non-null.

## 2. GenerationSnapshot

One row per completed generation (append-only during run).

| Field | Type | Notes |
|-------|------|--------|
| `experimentId` | string | FK |
| `generation` | int | 0-based or 1-based — pick one and document in contract (prefer **0-based** to match FORGE) |
| `fitnessMax` | number \| null | Best train fitness in gen |
| `fitnessAvg` | number \| null | Mean among valid |
| `fitnessMin` | number \| null | Optional |
| `bestPhenotype` | string \| null | Best of generation |
| `nInvalid` / `nFailedEval` | int \| null | From FORGE record when available |
| `recordedAt` | ISO-8601 | |

**Invariant**: Snapshots are written when the FORGE reporter fires — before the
full run completes — so clients can poll them while `status=running`.

## 3. FrozenStrategyEntry (020c)

First-class strategy catalogue row.

| Field | Type | Notes |
|-------|------|--------|
| `strategyId` | string | Canonical id registered in strategy registry |
| `displayName` | string | **Unique** among frozen entries |
| `phenotype` | string | Torque source; Torque-check at freeze |
| `sourceExperimentId` | string \| null | Provenance |
| `seed` | int \| null | |
| `fitnessId` | string \| null | |
| `trainFitness` / `validationFitness` | number \| null | Snapshot at freeze |
| `createdAt` | ISO-8601 | |

### Relationships

```text
EvolutionExperiment 1 ──* GenerationSnapshot
EvolutionExperiment 0..1 ──* FrozenStrategyEntry (provenance; optional)
FrozenStrategyEntry ── registered as Strategy in GET /strategies
```

## 4. Validation rules

| Rule | Enforcement |
|------|-------------|
| Split ratios sum ≈ 1.0 and each > 0 | Reject create |
| Candle count sufficient for split + strategy warmup | Reject create |
| `populationSize` ≥ 2, `nGenerations` ≥ 1 | Reject create |
| Second concurrent running experiment | Reject 409 |
| Freeze without best phenotype / non-terminal | Reject |
| Duplicate `displayName` (020c) | Reject; no overwrite |
| Phenotype fails Torque check (020c) | Reject freeze |
| 020b: empty leaves | Reject start |

## 5. Persistence mapping (plan default)

| Entity | Store |
|--------|--------|
| Experiment | `backend/data/uge_experiments/{id}/meta.json` |
| Generations | `.../generations.jsonl` |
| Frozen strategy | `backend/data/uge_frozen_strategies/{strategyId}.json` + in-process registry |
