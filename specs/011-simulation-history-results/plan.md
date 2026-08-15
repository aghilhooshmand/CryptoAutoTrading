# Implementation Plan: Simulation History & Results

**Branch**: `011-simulation-history-results` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 011 — list/filter persisted Simulation sessions;
dedicated detail route for inspect; freeze final-result snapshot at every stop
(and ledger-only backfill for pre-011 STOPPED); delete with confirmation and
fail-closed Portfolio binding rules; preserve refresh/nav reconnect; no
auto-resume, multi-active, Risk semantic changes, or second accounting engine.

## Summary

Add an inspection/persistence layer on top of Feature 003/009/010 Simulation
sessions: `GET` list (+ optional state filter, offset pagination with
`totalCount`, order `created_at DESC, id DESC`), enriched detail that uses
**frozen** `finalResult` as sole authoritative ending economics for STOPPED
sessions, and `DELETE` with safe guards. Persist a `finalResult` snapshot on
every transition to STOPPED (complete when valuation is trustworthy;
incomplete with null unverifiable metrics otherwise). Pre-existing STOPPED
rows get a one-time ledger-only backfill (never current market prices).
Frontend: History list on the Simulation tab of Auto Trading; dedicated detail
route `/auto-trading/simulation/:sessionId` (not a new top-level nav).
CONFIGURED may Start via existing Feature 003 path; STOPPED is
inspect/delete only. Execution/accounting remain authoritative; History does
not invent fills or unwind Portfolio. Recovery = fail-closed orphan→STOPPED +
freeze — not resume/worker recreation.

## Technical Context

**Language/Version**: Python 3.12; TypeScript + React 18+

**Primary Dependencies**: FastAPI, SQLAlchemy, SQLite, Vite, React Router.
Reuse `session_service` stop/get paths, journals, Feature 003 accounting
helpers (`liquidation_equity`, `session_net_pnl`), Feature 009 allocation
reads for delete guards, existing `/simulation/sessions/{id}` + journals +
`/sessions/active`.

**Storage**: Extend `simulation_sessions` with a frozen final-result payload
(JSON text column, Backtest `summary_json` pattern) + completeness metadata.
No new accounting tables. Journals unchanged. No FIFO purge (operator delete).

**Testing**: pytest unit (freeze completeness rules, ledger-only backfill,
immutability vs later marks); contract (list/filter, detail prefers freeze,
delete reject active/bound, delete cascade, Portfolio balances unchanged);
frontend Vitest (History list, detail route, delete confirm, refresh does not
stop); regression that RUNNING reconnect and Feature 010 Risk journal codes
still work.

**Target Platform**: Local developer machines; ~375px primary flow

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: List/detail for operator-scale session counts; no
distributed systems; avoid live mark fetch for STOPPED final metrics when
freeze exists

**Constraints**: Spec FR-001–FR-025 and clarify locks. History ≠ second
engine. No XT private. No auto-resume. No Feature 010 Risk changes. No
automatic retention eviction. Decision Log Mode (003/008 amendment) is a
prerequisite for correct History journal semantics — implement that amendment
before or as the first slice of 011 backend work, without renumbering roadmap
features.

**Scale/Scope**: One active Simulation; History reachable via offset pagination
(`totalCount`); no FIFO eviction

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Delete rejects while reserved/deployed binding; never unwind via History |
| II Simulation before real money | Pass | Simulation history only |
| III–IV Pipeline / Risk | Pass | No second engine; no Risk semantic changes |
| V Session boundaries | Pass | Inspect existing session bounds; no multi-active |
| VI Net P&L | Pass | Freeze authoritative liquidation-style terminal P&L when complete |
| VII Traceability | Pass | Config, journals, Risk reasons, freeze, stop reason |
| VIII Fail safe | Pass | Incomplete freeze + nulls; no invented marks/prices |
| IX Emergency stop | Pass | Unchanged; freeze after stop path |
| X Simplicity | Pass | JSON freeze on session; extend existing APIs |
| XII Evidence | Pass | Frozen metrics must not drift with later prices |
| XIII–XIV UI | Pass | List on Simulation page; detail route; 375px; confirm delete |
| XVI–XVIII | Pass | Public data only; no private XT |
| XXVII–XXXI | Pass | Spec/plan/tests; roadmap IN PROGRESS; no auto-commit |
| XXXIII Settings | Pass | No historical rewrite of Settings into old sessions |
| XXXIV Portfolio | Pass | Delete never releases reserved/deployed |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Freeze is a snapshot of Session accounting outcomes, not a parallel
ledger. Backfill never uses live market. Delete is cleanup-only with
fail-closed Portfolio checks. Detail route is nested under Auto Trading /
Simulation UX, not a new product surface.

## Project Structure

### Documentation (this feature)

```text
specs/011-simulation-history-results/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── simulation-history-api.md
└── tasks.md                 # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/app/db/models.py                      # EXTEND session: final_result_json (+ meta)
backend/app/db/session.py                     # Column ensure for new fields
backend/app/simulation/final_result.py        # NEW: build/freeze/backfill helpers
backend/app/simulation/session_service.py     # Freeze on stop; list; delete; detail dict
backend/app/simulation/pipeline.py            # Ensure auto-stop paths freeze
backend/app/simulation/recovery.py            # Freeze after restart → STOPPED
backend/app/api/simulation.py                 # GET list, DELETE; enrich GET detail
backend/tests/unit/test_simulation_final_result.py
backend/tests/contract/test_simulation_history_api.py
frontend/src/services/simulationApi.ts        # listSessions, deleteSession, finalResult types
frontend/src/features/simulation/             # History list + detail page components
frontend/src/pages/ or App routes             # Route /auto-trading/simulation/:sessionId
frontend/src/__tests__/simulationHistory*.tsx
```

**Structure Decision**: Extend the existing Simulation package and Auto Trading
UI. Mirror Backtest list/delete/summary patterns without copying Backtest FIFO
caps. No new top-level nav item.

## Complexity Tracking

> No constitution violations requiring justification.
