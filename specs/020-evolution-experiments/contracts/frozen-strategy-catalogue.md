# Contract: Frozen Strategy Catalogue (Feature 020c)

**Feature**: `020-evolution-experiments` (phase **020c**)  
**Date**: 2026-09-06  
**Depends on**: Terminal EvolutionExperiment with `bestPhenotype`; Feature 016
`check_phenotype` / `bind_phenotype`; Feature 005 strategy registry  
**Non-goals**: Mid-run freeze; overwrite on name clash; auto Real session

## `POST /uge/experiments/{id}/freeze`

Freeze best (or explicitly selected) phenotype into a **separate named
strategy**.

**Request**:

```json
{
  "displayName": "UGE BTC 1h Sept",
  "phenotype": null
}
```

- If `phenotype` is null/omitted → use experiment `bestPhenotype`.
- MVP: only **best** phenotype may be frozen (non-best selection out of scope).

**Responses**:

| Status | Meaning |
|--------|---------|
| 201 | Created; body = FrozenStrategyEntry + `strategyId` |
| 400 | Missing name, duplicate `displayName`, Torque check fail, no phenotype |
| 409 | Experiment not terminal |

**Uniqueness**: `displayName` unique among frozen entries — **reject**, never
overwrite or auto-suffix.

## Catalogue listing

Frozen entries MUST appear in existing `GET /strategies` (or equivalent) as
normal strategies:

```json
{
  "id": "uge_frozen_<slug_or_uuid>",
  "displayName": "UGE BTC 1h Sept",
  "parameters": [],
  "origin": "uge_frozen"
}
```

Exact `origin` field optional if UI can distinguish via id prefix / metadata.

## Using frozen strategies

- **Backtest** / **Simulation**: `strategyId` = frozen id; empty or omitted
  `strategyParams` (phenotype is bound inside factory).
- **Real** (when Feature 015 create exists): same `strategyId` selection;
  Evolution lab MUST NOT create Real sessions.

## Registry behavior

- Persist JSON (or DB) under `backend/data/uge_frozen_strategies/`.
- On process start, register each entry via `register(StrategyRegistration)`.
- Factory: `bind_phenotype(stored_phenotype)` → `Strategy`.
- `min_history_candles` delegated to bound strategy.

## Tests (acceptance)

- Freeze → `GET /strategies` contains id → Backtest create+run succeeds.
- Duplicate displayName → 400; first entry unchanged.
- Freeze while `running` → 409/400.
