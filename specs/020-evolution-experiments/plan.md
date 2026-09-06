# Implementation Plan: Evolution Experiments & Results (UGE Lab)

**Branch**: `020-evolution-experiments` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature 020 — dedicated Evolution / Experiments UI to run FORGE UGE
offline, stream each generation, chart fitness, configure structured search
space (020b), and freeze best phenotypes as **separate named strategies**
(020c) for Backtest / Simulation / Real selection. Lab never auto-places Real
orders. Operator lock: UGE lab now (015 paused). Clarifications Session
2026-09-06 apply.

## Summary

Extend Feature 019 `uge_search` into an **experiment runner + HTTP lab API +
frontend Evolution area**, delivered in three shippable phases:

| Phase | Deliver |
|-------|---------|
| **020a** | Create/start/cancel one experiment; background in-process run; persist generation snapshots as each gen completes; HTTP progress + history; UI config + live chart + best phenotype; **no** named strategy freeze |
| **020b** | Structured leaf/operator/discrete-param controls → system-built `Grammar`; no raw BNF UI |
| **020c** | Terminal-only freeze → unique display-name catalogue strategy; selectable in Backtest/Sim/(Real when enabled) |

Reuse: `run_uge_search` / fitness / splits / Torque bind / `StatsReporter`-style
FORGE `reporters=` hook. Do not vendor FORGE. Do not add WebSockets or a
distributed queue (constitution X — justified single in-process runner +
polling/SSE).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/React (frontend Vite).

**Primary Dependencies**: FastAPI; existing SQLAlchemy/SQLite patterns where
needed; FORGE `uge` (`UGEEngine`, `Grammar`, `StatsReporter` / custom
`reporters`); Feature 019 `app.uge_search`; Feature 016 `torque_bind`; Feature
004/003 pipeline via evaluate; frontend charts (reuse existing chart libs if
present, else lightweight SVG/canvas).

**Storage**: Experiment + generation JSON (and/or SQLite rows) under
`backend/data/uge_experiments/` (or DB tables if aligning with existing
session persistence). Frozen strategies (020c): durable catalogue store +
dynamic registry registration at process start.

**Testing**: pytest unit (job singleton, cancel, generation append, grammar
builder, freeze uniqueness); integration (tiny pop/ngen streamed gens visible
via API before run ends); frontend Vitest (Evolution form, progress chart
smoke, freeze form 020c); import guards (no Real place from lab).

**Target Platform**: Local operator app (same as 019).

**Project Type**: Web application (`backend/` + `frontend/`).

**Performance Goals**: First generation summary visible after that generation’s
population finishes (SC-001); no full-run wait for gen-1 UI. Fixture runs
(pop≤8, ngen≤3) complete in developer-interactive time.

**Constraints**: Constitution I–IV, VIII, X, XII, XXXV–XXXVIII, XL; single
active experiment; train-only selection; per-generation progress (not per
individual); no raw BNF UI; no mid-run freeze; reject duplicate freeze names;
no auto Real from lab; no FORGE source copy.

**Scale/Scope**: One operator; one concurrent run; MVP grammar default (020a);
structured subset of registry leaves + `and`/`or`/`vote` (020b); N frozen
named strategies (020c).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Lab does not place orders; freeze → same Controller/Risk path |
| II Simulation before real | Pass | Offline Backtest fitness; Real only via operator session later |
| III Single pipeline | Pass | Phenotypes → 016 → Controller/Risk |
| IV Controller / Risk | Pass | No bypass |
| VIII Fail safe | Pass | Invalid start/freeze fail closed |
| X Intentional simplicity | Pass* | *One in-process runner + poll/SSE justified by FR-004; no distributed queue/WebSocket |
| XII Evidence | Pass | UI must not imply guaranteed profit |
| XXXV Torque | Pass | Phenotypes remain Torque strings |
| XXXVI GE | Pass | Call FORGE uge; own grammar/fitness |
| XXXVII Fitness | Pass | Reuse 019 allow-list |
| XXXVIII Leakage | Pass | Train-only selection unchanged |
| XL Reuse | Pass | Extend uge_search; do not fork GE |

**Gate**: PASS (simplicity exception documented in Complexity Tracking).

### Post-design Constitution Check

PASS. Design uses FORGE `reporters` for per-generation hooks; persists
snapshots; UI polls (or optional SSE) — no WebSocket requirement; freeze is
operator-driven catalogue registration only; Real untouched by lab.

## Project Structure

### Documentation (this feature)

```text
specs/020-evolution-experiments/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── evolution-experiments-api.md
│   └── frozen-strategy-catalogue.md   # 020c
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/app/uge_search/
├── runner.py                 # EXTEND: reporters, cancel token, grammar inject
├── grammar_builder.py        # NEW 020b: structured → BNF / Grammar
├── experiment_store.py       # NEW: persist experiment + generations
├── experiment_runner.py      # NEW: singleton job, background thread
├── experiment_service.py     # NEW: validate config, load candles, start job
├── frozen_catalogue.py       # NEW 020c: named strategies store + register
└── ... (019 modules unchanged in role)

backend/app/api/
├── uge.py                    # EXTEND or split → evolution routes
└── ... 

backend/app/main.py           # mount routes; load frozen catalogue on startup

frontend/src/features/evolution/
├── EvolutionPage.tsx         # NEW nav area
├── ExperimentConfigForm.tsx  # 020a params; 020b structured controls
├── ExperimentProgress.tsx    # generation list + chart
├── FreezeStrategyForm.tsx    # 020c
└── evolutionApi.ts

frontend/src/ (nav + routes)  # link Evolution

backend/tests/unit/test_uge_experiment_*.py
backend/tests/integration/test_uge_experiment_stream.py
backend/tests/integration/test_frozen_catalogue_backtest.py  # 020c
frontend/src/__tests__/evolution*.test.tsx
```

**Structure Decision**: Keep search math in `uge_search`; add experiment job +
store + (020c) catalogue beside it; dedicated `frontend/src/features/evolution`
(not only Backtest). Phased implementation: land 020a paths first.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| In-process background run thread (not a distributed worker/queue) | Spec requires UI to remain responsive and show gens before full completion | Synchronous HTTP request blocks until all gens finish — violates SC-001 / FR-004 |
| Progress transport (HTTP poll preferred; optional SSE) | Stream each completed generation to UI | WebSockets banned by constitution X without need; poll meets FR-004 with less infra |
