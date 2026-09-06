# Research: Evolution Experiments & Results (UGE Lab)

**Feature**: `020-evolution-experiments`  
**Date**: 2026-09-06  
**Depends on**: Feature 019 `uge_search`, FORGE `uge` reporters, Feature 016

## R1 — How to observe each generation while UGE runs

**Decision**: Pass a custom callable (or thin wrapper around FORGE
`StatsReporter`) via `engine.run(..., reporters=[...])`. On each generation,
append a `GenerationSnapshot` to the experiment store (best/mean/worst fitness,
best phenotype, generation index, timestamp). Extend `run_uge_search` (or a
sibling `run_uge_search_with_hooks`) to accept `on_generation` + `cancel_check`.

**Rationale**: FORGE already supports `reporters=` and `StatsReporter` fills
`fitness_max` / `fitness_avg` / `best_phenotype` per generation
(`uge.observe.stats`). No need to poll internals of `UGEEngine`.

**Alternatives considered**:

| Option | Why rejected |
|--------|----------------|
| Only read `outcome.generation_records` after `run` returns | Cannot stream mid-run (fails FR-004 / SC-001) |
| Patch FORGE loop | Forbidden — no FORGE source edits/vendor |
| Per-individual fitness stream | Spec: per generation only; noisier and costlier |

## R2 — Job execution model (singleton)

**Decision**: At most one active experiment. `POST .../experiments` starts a
**daemon/background thread** (or `asyncio.to_thread`) that runs UGE; request
returns `202` + experiment id. Second start while `running` → `409`. Cancel sets
a thread-safe flag; reporter raises/stops at generation boundary (cancel latency
≈ one generation evaluation time).

**Rationale**: Constitution X forbids distributed queues/workers without need.
One local thread is the minimum that keeps FastAPI responsive.

**Alternatives considered**:

| Option | Why rejected |
|--------|----------------|
| Sync `POST` until done | Blocks UI; no mid-run gens |
| Celery/RQ/redis queue | Distributed complexity unjustified for single-operator app |
| Subprocess | Harder cancel/share store; more moving parts for MVP |

## R3 — Progress transport to the UI

**Decision**: **Primary**: `GET /uge/experiments/{id}` (and/or
`.../generations`) polled by the UI every ~1s while status is `running`.
**Optional stretch**: SSE `text/event-stream` if polling proves awkward — still
no WebSockets.

**Rationale**: Spec needs “see each generation as it completes,” not a
push-protocol mandate. Polling is simplest, testable, and constitution-friendly.
Generation rows are durable as soon as the reporter fires, so poll catches them.

**Alternatives considered**:

| Option | Why rejected / deferred |
|--------|-------------------------|
| WebSockets | Explicit constitution X discouragement |
| SSE-only | Fine later; poll sufficient for SC-001 |
| Long-poll | More complex than fixed-interval poll |

## R4 — Persistence format

**Decision**: JSON files under `backend/data/uge_experiments/{id}/`:
`meta.json` (config, status, best, timings) + `generations.jsonl` (append one
object per generation). List experiments by scanning directory. 019
`uge_runs/` frozen artifacts remain for backward compatibility; 020a does not
require promoting them to named strategies.

**Rationale**: Matches 019 file-based MVP; easy to inspect; no new DB migration
required for 020a. 020c may add `backend/data/uge_frozen_strategies/{id}.json`
(or a small SQLite table) for catalogue durability.

**Alternatives considered**:

| Option | Why rejected for 020a |
|--------|------------------------|
| Full SQL models for every gen | Heavier; defer unless file I/O becomes painful |
| Memory-only | Fails reconnect + reproducibility (FR-008) |

## R5 — Candle window for experiments

**Decision**: Experiment create body includes symbol, timeframe, start/end (or
equivalent window). Server loads closed candles via existing market-data /
backtest fetch path used by Feature 004; reject if insufficient for split +
warmup.

**Rationale**: Same historical source as Backtest; no new venue.

## R6 — Structured grammar builder (020b)

**Decision**: `grammar_builder.build_grammar(leaves, composition_ops, param_alts)`
emits BNF text compatible with FORGE `Grammar.from_text`, constrained to
registry ParamDef names and discrete allow-lists (defaults from
`trading_mvp.bnf`). UI sends structured JSON only — never raw BNF.

**Rationale**: Clarification Session 2026-09-06 Option B; keeps search space
product-safe.

**Alternatives considered**: Raw BNF editor (rejected by clarify); presets-only
(too weak vs operator request).

## R7 — Named frozen strategies (020c)

**Decision**: Each freeze creates a durable catalogue record with unique
`displayName`, stable `strategyId` (e.g. `uge_frozen_<slug>` or uuid), and
phenotype string. On API startup (and after freeze), `register()` a
`StrategyRegistration` whose factory binds via `bind_phenotype(phenotype)`
(params empty or fixed). `GET /strategies` lists them beside built-ins.
Duplicate `displayName` → 400. Freeze only if experiment status is terminal and
`bestPhenotype` (or selected retained individual) exists.

**Rationale**: Clarifications A/A/A for catalogue shape, terminal-only, reject
duplicates. Distinct from 019 `torque_phenotype` free-text / artifact picker.

**Alternatives considered**: Preset under single `torque_phenotype` (rejected);
overwrite on name clash (rejected).

## R8 — Phase gate for implementation

**Decision**: Implement and gate-test **020a** before 020b/020c code lands in
the same branch as optional follow-on commits; Feature 020 not DONE until all
three phases meet spec SCs. Tasks.md SHOULD label `[020a]` / `[020b]` / `[020c]`.

**Rationale**: Operator asked for three parts; reduces blast radius.

## R9 — Charts

**Decision**: Frontend chart of generation index vs `fitnessMax` and
`fitnessAvg` (or mean) from polled generation snapshots. No matplotlib in
backend for UI; FORGE `visualize` remains optional offline tool, not product UI.

**Rationale**: Spec asks FORGE-*like* inspectability, not embedding FORGE
notebook UI.
