# Tasks: Simulation History & Results

**Input**: Design documents from `/specs/011-simulation-history-results/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required — unit (freeze/backfill), contract (list/detail/delete),
frontend Vitest (History list/detail/delete confirm/refresh), per plan.md and
constitution XXVIII / SC-001–SC-006.

**Organization**: Extend existing Simulation package + Auto Trading UI. History
is inspection only — no second accounting engine. No Feature 010 Risk semantic
changes. No auto-resume / multi-active. Propose commits only; do not
auto-commit. Keep Feature 011 `IN PROGRESS` on `docs/ROADMAP.md` until
completion workflow.

**Spec precedence** (clarify 2026-08-15 + analyze remediation):
- Pre-011 backfill: ledger only; never current/new market prices
- Always persist final-result snapshot; incomplete → null unverifiable metrics
- Delete reject while Portfolio reserved/deployed binding; never unwind Portfolio
- STOPPED from History: inspect + delete only (no restart/resume)
- CONFIGURED may use existing Feature 003 Start (reuse; no second start stack)
- History list on Simulation page; detail route **`/auto-trading/simulation/:sessionId`**
- List order: `created_at DESC, id DESC`; offset pagination limit 50/max 100, offset 0, `totalCount`
- STOPPED with finalResult: freeze is sole authoritative ending economics (no drifting live mark P&L)
- Recovery = orphan→STOPPED + freeze; not resume/worker recreation
- Decision journals: persisted only; show `decisionLogMode`; never fabricate HOLDs (003/008 Decision Log Mode amendment)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US5 map to spec user stories

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/011-simulation-history-results/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

**Purpose**: Confirm extension surfaces; no new trading engine package

- [x] T001 Confirm reusable Simulation/API/UI surfaces per plan.md (`backend/app/simulation/session_service.py`, `backend/app/simulation/pipeline.py`, `backend/app/simulation/recovery.py`, `backend/app/api/simulation.py`, `backend/app/db/models.py`, `frontend/src/services/simulationApi.ts`, `frontend/src/features/simulation/`, `frontend/src/pages/AutoTradingPage.tsx`, `frontend/src/App.tsx`) — extend; do not create a second accounting engine. **Prerequisite**: Feature 003/008 Decision Log Mode amendment tasks (003 T075–T079, 008 T051–T053) documented; implement that amendment before History journal UX relies on mode.
- [x] T002 [P] Confirm Backtest list/delete/summary patterns to mirror (API shape only, not FIFO caps) in `backend/app/api/backtest.py` and `frontend/src/features/backtest/BacktestRunList.tsx`

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Schema + freeze/backfill helpers shared by all stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [x] T003 Extend `SimulationSessionRow` with nullable `final_result_json` (TEXT) in `backend/app/db/models.py` per `data-model.md`
- [x] T004 [P] Ensure SQLite column add path for `final_result_json` in `backend/app/db/session.py` (match existing `_ensure_column` pattern)
- [x] T005 Create `backend/app/simulation/final_result.py` with build/serialize helpers: complete flat (cash-based), complete long+safe mark (liquidation equity), incomplete (null ending/net/return), `source` ∈ `stop|recovery|backfill`, decimal-string fields per `data-model.md` / `contracts/simulation-history-api.md`
- [x] T006 Implement ledger-only `ensure_final_result_backfill(db, row)` in `backend/app/simulation/final_result.py` — never call Feature 002 quotes; idempotent; flat→complete, long→incomplete
- [x] T007 [P] Unit tests for completeness rules and backfill-never-fetches-market in `backend/tests/unit/test_simulation_final_result.py`
- [x] T008 Add `list_sessions` / `delete_session` / `session_to_dict` enrichment hooks scaffolding in `backend/app/simulation/session_service.py` (wire full behavior in story phases)

**Checkpoint**: Column + freeze/backfill helpers ready; stop paths not yet freezing; list/delete not yet public

---

## Phase 3: User Story 1 - Browse and reopen past Simulations (Priority: P1) 🎯 MVP

**Goal**: List sessions (filter by state); open dedicated detail with config, journals, timestamps; STOPPED shows no restart.

**Independent Test**: Several STOPPED + optional RUNNING → History list distinguishes states → open STOPPED detail → config/journals/times match; no run-again.

### Tests

- [x] T009 [P] [US1] Contract tests for `GET /simulation/sessions` in `backend/tests/contract/test_simulation_history_api.py`: order `created_at DESC, id DESC`; optional `state` filter; `limit` default 50 / max 100; `offset` default 0; response includes `totalCount`; invalid state/limit/offset → `invalid_query`; second page via offset returns older sessions
- [x] T010 [P] [US1] Contract tests for `GET /simulation/sessions/{id}` including `finalResult` after ledger backfill when JSON missing in `backend/tests/contract/test_simulation_history_api.py`
- [x] T011 [P] [US1] Frontend tests for History list + navigate to `/auto-trading/simulation/:sessionId` (no new top-level nav); list uses offset pagination with `totalCount` in `frontend/src/__tests__/simulationHistoryList.test.tsx`

### Implementation

- [x] T012 [US1] Implement `list_sessions` (`state`, `limit` default 50 max 100, `offset` default 0, `totalCount`) ordered `created_at DESC, id DESC` in `backend/app/simulation/session_service.py`; call backfill for STOPPED missing freeze
- [x] T013 [US1] Add `GET /simulation/sessions` in `backend/app/api/simulation.py` per `contracts/simulation-history-api.md` (preserve `/sessions/active` routing)
- [x] T014 [US1] Enrich `GET /simulation/sessions/{id}` with `finalResult` (ensure backfill) in `backend/app/simulation/session_service.py` / `backend/app/api/simulation.py` — for STOPPED with `finalResult`, do not expose drifting live mark-based ending equity/net P&L/return
- [x] T015 [US1] Extend `frontend/src/services/simulationApi.ts` with `listSessions` (`limit`/`offset`/`totalCount`), `FinalResult` types, and detail parsing of `finalResult`
- [x] T016 [US1] Add History list UI on Simulation tab in `frontend/src/features/simulation/` (e.g. `SimulationHistoryList.tsx`) with offset pagination wired into `frontend/src/pages/AutoTradingPage.tsx`
- [x] T017 [US1] Add detail route `/auto-trading/simulation/:sessionId` in `frontend/src/App.tsx` + detail component under `frontend/src/features/simulation/`: config (including effective **`decisionLogMode`**), trades, decisions (Risk reasons; persisted rows only — no fabricated HOLDs), timestamps, stop reason; **STOPPED** = inspect only (delete in US3); **CONFIGURED** may expose existing Feature 003 Start (reuse; no second start); no new top-level nav
- [x] T018 [US1] Run T009–T011 until green (`backend/tests/contract/test_simulation_history_api.py`, `frontend/src/__tests__/simulationHistoryList.test.tsx`)

**Checkpoint**: MVP — operators can list and reopen historical Simulations

---

## Phase 4: User Story 2 - Frozen final results that do not drift (Priority: P1)

**Goal**: Persist freeze on every STOPPED path; complete vs incomplete; immutable after market price change.

**Independent Test**: Stop with complete valuation → note metrics → change marks → reopen → identical `finalResult`; incomplete path keeps nulls.

### Tests

- [x] T019 [P] [US2] Unit tests: stop-time complete/incomplete builders and no overwrite of existing freeze with later marks in `backend/tests/unit/test_simulation_final_result.py`
- [x] T020 [P] [US2] Contract tests: after stop, `finalResult` present; after mocking/changing quotes, GET detail `finalResult` unchanged in `backend/tests/contract/test_simulation_history_api.py`

### Implementation

- [x] T021 [US2] Call persist freeze from `stop_session_async` in `backend/app/simulation/session_service.py` after flatten + STOPPED (pass safe mark only when available at stop)
- [x] T022 [P] [US2] Ensure auto-stop paths that reach STOPPED persist freeze in `backend/app/simulation/pipeline.py`
- [x] T023 [P] [US2] Persist freeze after orphan recovery marks STOPPED in `backend/app/simulation/recovery.py` (`source=recovery`; long without mark → incomplete). Recovery = fail-closed orphan→STOPPED + freeze — not resume/worker recreation
- [x] T024 [US2] For STOPPED with `finalResult`, History/detail API and UI use freeze as sole authoritative ending economics (no drifting live mark ending P&L); RUNNING keeps live `economics` in `backend/app/simulation/session_service.py` and `frontend/src/features/simulation/`
- [x] T025 [US2] Show frozen Final results block (complete badge / incomplete + nulls) on detail page in `frontend/src/features/simulation/`
- [x] T026 [US2] Run T019–T020 until green (`backend/tests/unit/test_simulation_final_result.py`, `backend/tests/contract/test_simulation_history_api.py`)

**Checkpoint**: Terminal economics frozen; history does not drift with live prices

---

## Phase 5: User Story 3 - Delete historical Simulations safely (Priority: P2)

**Goal**: Confirm delete for eligible sessions; reject RUNNING/STOPPING and active Portfolio binding; cascade journals; never unwind Portfolio.

**Independent Test**: DELETE RUNNING → 409; bound reserved/deployed → 409 Portfolio unchanged; eligible STOPPED → 204 gone from list.

### Tests

- [x] T027 [P] [US3] Contract tests: `DELETE` → 204 cascade; `409 session_active`; `409 portfolio_binding_active`; Portfolio balances unchanged in `backend/tests/contract/test_simulation_history_api.py`
- [x] T028 [P] [US3] Frontend tests: delete confirm required; reject messaging; list refresh in `frontend/src/__tests__/simulationHistoryDelete.test.tsx`

### Implementation

- [x] T029 [US3] Implement `delete_session` with state + Portfolio reserved/deployed binding guards (no Portfolio release) and journal cascade in `backend/app/simulation/session_service.py`
- [x] T030 [US3] Add `DELETE /simulation/sessions/{id}` in `backend/app/api/simulation.py` per contract error codes
- [x] T031 [US3] Add `deleteSession` to `frontend/src/services/simulationApi.ts`
- [x] T032 [US3] Wire delete + explicit confirm on History list/detail in `frontend/src/features/simulation/` (STOPPED/CONFIGURED when eligible; STOPPED never restart/resume)
- [x] T033 [US3] Run T027–T028 until green (`backend/tests/contract/test_simulation_history_api.py`, `frontend/src/__tests__/simulationHistoryDelete.test.tsx`)

**Checkpoint**: Safe History cleanup without Portfolio unwind

---

## Phase 6: User Story 4 - Stay connected without stopping (Priority: P2)

**Goal**: Navigation / refresh / remount do not stop active backend Simulation; reconnect preserved.

**Independent Test**: Start RUNNING → refresh → still RUNNING → reconnect via active and/or History.

### Tests

- [x] T034 [P] [US4] Frontend regression: remount/refresh path does not call stop in `frontend/src/__tests__/simulationHistoryReconnect.test.tsx` (extend patterns from `frontend/src/__tests__/simulationResponsive.test.tsx` / `useSimulationSession`)
- [x] T035 [P] [US4] Contract/smoke: `GET /simulation/sessions/active` still returns RUNNING after list/detail traffic in `backend/tests/contract/test_simulation_history_api.py` or existing simulation contract file

### Implementation

- [x] T036 [US4] Audit `frontend/src/features/simulation/useSimulationSession.ts` and History/detail mount effects — ensure no stop-on-unmount; active reconnect still works alongside History list
- [x] T037 [US4] From History, opening RUNNING session uses reconnect/live viewer behavior without implying multi-active create in `frontend/src/features/simulation/` / `frontend/src/pages/AutoTradingPage.tsx`
- [x] T038 [US4] Run T034–T035 until green (`frontend/src/__tests__/simulationHistoryReconnect.test.tsx`, `backend/tests/contract/test_simulation_history_api.py`)

**Checkpoint**: History UI does not regress Feature 003 reconnect semantics

---

## Phase 7: User Story 5 - Responsive operator History UI (Priority: P3)

**Goal**: List → detail → delete-confirm usable ~375px; critical facts not hover-only.

**Independent Test**: ~375px complete list → detail → confirm/cancel delete without losing primary actions.

### Tests

- [x] T039 [P] [US5] Vitest/responsive checks for History list + detail + delete confirm at narrow width in `frontend/src/__tests__/simulationHistoryResponsive.test.tsx`

### Implementation

- [x] T040 [US5] Apply `docs/UI_UX_STANDARDS.md` layout to History list/detail (labels SIMULATION, confirm destructive, primary actions reachable ~375px) in `frontend/src/features/simulation/`
- [x] T041 [US5] Run T039 until green (`frontend/src/__tests__/simulationHistoryResponsive.test.tsx`)

**Checkpoint**: Operator History usable on narrow viewports

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Quickstart validation, regressions, docs hygiene, FR-020 negatives

- [x] T042 [P] Run full quickstart automated checks: `pytest backend/tests/unit/test_simulation_final_result.py`, `pytest backend/tests/contract/test_simulation_history_api.py`, and frontend `simulationHistory*` Vitest targets
- [x] T043 [P] Regression: Feature 010 Risk journal codes still visible on historical session detail; History does **not** fabricate HOLD rows; detail shows effective `decisionLogMode` (`backend/tests/contract/` + frontend journal/history display)
- [x] T044 [P] Confirm no new top-level nav item and primary nav tests still pass in `frontend/src/__tests__/primaryNavigation.test.tsx`
- [x] T045 [P] Negative coverage for FR-020 in `backend/tests/contract/test_simulation_history_api.py` (and UI assert if needed): Feature 011 does **not** introduce resume of STOPPED sessions, restart of the same historical session id, or worker recreation after backend restart; orphan recovery remains RUNNING/STOPPING→STOPPED then freeze/backfill only
- [x] T046 Update `specs/011-simulation-history-results/quickstart.md` notes if commands/paths differ after implementation
- [x] T047 Propose commit message(s) only (do not auto-commit); leave `docs/ROADMAP.md` Feature 011 as IN PROGRESS until DONE workflow
- [x] T048 [P] History/contract test: `important_only` session History detail journal has no fabricated HOLDs; `full_audit` may include HOLD; `decisionLogMode` visible on detail in `backend/tests/contract/test_simulation_history_api.py` and/or `frontend/src/__tests__/simulationHistoryList.test.tsx`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: Start immediately
- **Phase 2 Foundational**: After Setup — **BLOCKS** all user stories
- **Phase 3 US1**: After Foundational — MVP
- **Phase 4 US2**: After Foundational; ideally after US1 detail exists (can start backend freeze in parallel with US1 UI)
- **Phase 5 US3**: After Foundational; UI delete best after US1 list/detail
- **Phase 6 US4**: After US1 History mounts exist
- **Phase 7 US5**: After US1 + US3 UI surfaces exist
- **Phase 8 Polish**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependency on US2–US5 for list/reopen MVP (backfill supplies freeze for legacy STOPPED)
- **US2 (P1)**: After Phase 2 — freeze-on-stop; integrates with US1 detail display
- **US3 (P2)**: After Phase 2 — delete API independent; UI needs US1 list/detail
- **US4 (P2)**: Needs US1 History integration points
- **US5 (P3)**: Needs US1 (+ US3 for delete-confirm path)

### Parallel Opportunities

- T001–T002 parallel in Setup
- T003–T004 parallel; T007 parallel after T005–T006
- T009–T011 parallel; T022–T023 parallel after T021 pattern exists
- T027–T028 parallel; T034–T035 parallel
- After Phase 2: backend US2 freeze wiring can proceed while US1 frontend list is built

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract GET list in backend/tests/contract/test_simulation_history_api.py"
Task: "Contract GET detail+finalResult backfill in backend/tests/contract/test_simulation_history_api.py"
Task: "Frontend History list in frontend/src/__tests__/simulationHistoryList.test.tsx"

# After list service exists:
Task: "GET /simulation/sessions API"
Task: "simulationApi listSessions types"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (schema + backfill helpers)
3. Phase 3 US1 list + detail route
4. **STOP and VALIDATE** independent test for browse/reopen

### Incremental Delivery

1. US1 → list/reopen MVP
2. US2 → freeze immutability (critical trust)
3. US3 → safe delete
4. US4 → reconnect regression lock
5. US5 → responsive polish
6. Phase 8 quickstart + propose commits

### Suggested MVP Scope

**US1 only** (with Phase 2): operators can find and inspect past Simulations.
Deliver US2 immediately after for trustworthy frozen P&L.

---

## Notes

- [P] = different files / no incomplete dependency
- Do not invent market prices for backfill or incomplete freeze
- Do not unwind Portfolio on delete
- Do not add top-level nav solely for History
- Do not auto-commit; do not mark roadmap DONE here
