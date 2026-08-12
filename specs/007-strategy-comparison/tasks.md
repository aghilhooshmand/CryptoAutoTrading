# Tasks: Strategy Comparison and Evaluation

**Input**: Design documents from `/specs/007-strategy-comparison/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context and SC-001–SC-008 / quickstart require orchestrator unit tests, comparison contract tests, shared-candle integration, retention, backtest history `origin` filter, and frontend comparison UI coverage (no winner badge).

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Spec precedence** (Session 2026-08-12 clarifications + plan):
- **2–5 legs**; duplicate strategy ids allowed with different params
- **Synchronous**: one shared candle fetch; return only after final state; no async/polling/WebSockets
- Legs = normal `BacktestRun` with `origin=comparison`; default history **hides** them
- Retention: **10** completed + **5** failed comparisons (FIFO); legs follow Feature 004 retention
- Both `roundTripCount` and `fillCount` required on every completed leg
- No automatic “best/winner”; reuse Feature 004 `run_engine` + 005/006 registry only
- Fail-closed if any leg fails after accept; strictest-leg `min_history` gate
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/007-strategy-comparison/`, root `README.md` only if needed

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm Feature 004–006 touch points; create package/test stubs

- [X] T001 Verify backtest engine/service/repository and strategy registry paths exist (`backend/app/backtest/engine.py`, `backend/app/backtest/service.py`, `backend/app/strategy/registry.py`, `frontend/src/features/backtest/`, `frontend/src/features/strategy/StrategyConfigFields.tsx`) per plan.md
- [X] T002 [P] Create empty package layout `backend/app/comparison/` (`__init__.py`) and confirm `backend/tests/unit/`, `backend/tests/contract/`, `backend/tests/integration/` are ready for comparison test files
- [X] T003 [P] Create frontend feature folder stub `frontend/src/features/comparison/` and `frontend/src/services/comparisonApi.ts` placeholder exports (types only) per plan.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, origin tagging, candle-reuse helper, comparison retention — blocks all user stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T004 Add `origin` (`manual` \| `comparison`) and optional `comparison_id` on `BacktestRunRow` in `backend/app/db/models.py`; ensure create/migrate path initializes defaults for existing rows
- [X] T005 Add `StrategyComparison` / `ComparisonLeg` tables (or equivalent rows) in `backend/app/db/models.py` per `data-model.md` (sequential after T004 — same file)
- [X] T006 Implement comparison repository with FIFO retention (10 completed / 5 failed) in `backend/app/comparison/repository.py` per research Decision 6
- [X] T007 Extract or add “run with prefetched candles” helper in `backend/app/backtest/service.py` (reuse `run_engine`) so comparison legs do not re-fetch per research Decision 1
- [X] T008 [P] Map engine `summary_json` → comparison leg metrics (`fillCount` ← `strategyFillCount`, `vsBuyAndHoldReturnPct`) in `backend/app/comparison/metrics.py` per research Decision 5
- [X] T009 Extend `GET /backtest/runs` list filtering in `backend/app/backtest/repository.py` and `backend/app/api/backtest.py` so default excludes `origin=comparison`; support include flag per `contracts/strategy-comparison-api.md`
- [X] T010 [P] Unit tests for comparison retention FIFO in `backend/tests/unit/test_comparison_retention.py`
- [X] T011 [P] Contract/unit coverage that default backtest list hides comparison-originated runs in `backend/tests/contract/test_backtest_api.py` (extend)
- [X] T012 Run Dual EMA continuity baseline: `pytest backend/tests/unit/test_dual_ema_continuity.py -q` must pass before comparison orchestration (no Feature 004/006 regressions)

**Checkpoint**: Schema + helpers + history filter ready; user stories can build orchestrator/UI

---

## Phase 3: User Story 1 - Run a fair multi-strategy comparison (Priority: P1) 🎯 MVP

**Goal**: Synchronous `POST /comparisons` with shared window/money, 2–5 legs, one candle fetch, per-leg `run_engine`, completed summary table metrics (no winner badge); basic Auto Trading UI to create and view results.

**Independent Test**: Create comparison with `dual_ema` + `rsi` defaults on a valid window; receive completed comparison with shared B&H and both legs showing required metrics including `roundTripCount` and `fillCount`; reject 1 or 6 legs.

### Tests for User Story 1

- [X] T013 [P] [US1] Unit tests for orchestrator: leg count 2–5, strictest `S` gate, fail-closed on leg failure, shared candles, and comparison-in-flight lock behavior (no false conflict with Feature 004 single-run lock) in `backend/tests/unit/test_comparison_orchestrator.py`
- [X] T014 [P] [US1] Contract tests for `POST /comparisons`: `201` + `status=completed` on success; `201` + `status=failed` after accept failures; `400` pre-accept (invalid legs/params/oversized, no row) in `backend/tests/contract/test_comparison_api.py`
- [X] T015 [P] [US1] Integration test: two strategies on fixed fixture → deterministic shared-candle metrics in `backend/tests/integration/test_comparison_shared_candles.py`

### Implementation for User Story 1

- [X] T016 [US1] Implement sync comparison orchestrator in `backend/app/comparison/service.py` (validate shared config + legs, fetch once, run legs via prefetched helper, persist comparison, fail-closed; hold a comparison-level in-flight lock per research Decision 3 so multi-leg persistence does not trip Feature 004 `backtest_already_running` incorrectly) per FR-001–FR-006 / FR-003a / FR-009
- [X] T017 [US1] Implement `POST /comparisons` (and mount router) in `backend/app/api/comparison.py` and `backend/app/main.py` per `contracts/strategy-comparison-api.md` (`201` for completed and post-accept failed; `409` when a comparison is already in flight)
- [X] T018 [P] [US1] Implement `listComparisons` / `createComparison` client in `frontend/src/services/comparisonApi.ts`
- [X] T019 [US1] Build comparison config form + results table (all FR-006 metrics; **no** best/winner chrome) in `frontend/src/features/comparison/` and host on `frontend/src/pages/AutoTradingPage.tsx`
- [X] T020 [P] [US1] Frontend tests: create payload 2 legs; reject UI for &lt;2/&gt;5; assert no winner badge in `frontend/src/__tests__/comparison.test.tsx`
- [X] T021 [US1] Run T012–T015 and T020; fix until passing

**Checkpoint**: MVP — fair sync comparison create + results visible under Auto Trading

---

## Phase 4: User Story 2 - Inspect each strategy’s underlying backtest (Priority: P1)

**Goal**: Each completed leg links to a normal backtest run marked `origin=comparison`; operator inspects summary/journals; default main history hides comparison legs; filter can include them.

**Independent Test**: After a completed comparison, open each `backtestRunId`; journals present; default backtest list omits those runs; include-comparison shows them with origin mark.

### Tests for User Story 2

- [X] T022 [P] [US2] Contract tests: comparison response includes `backtestRunId`; get run exposes `origin=comparison`; default list excludes; include flag lists them in `backend/tests/contract/test_comparison_api.py` and `backend/tests/contract/test_backtest_api.py` (extend)
- [X] T023 [P] [US2] Frontend tests: drill-down to leg detail; default history hides comparison origin in `frontend/src/__tests__/comparisonInspect.test.tsx` (and/or extend backtest list tests)

### Implementation for User Story 2

- [X] T024 [US2] Ensure orchestrator persists each leg as `BacktestRun` with `origin=comparison` and `comparison_id` in `backend/app/comparison/service.py` / backtest create helper
- [X] T025 [US2] Expose `origin` (+ optional `comparisonId`) on backtest run API payloads in `backend/app/backtest/service.py` (serialize) and `frontend/src/services/backtestApi.ts`
- [X] T026 [US2] Wire comparison results “inspect leg” to existing backtest results/journals UI from `frontend/src/features/comparison/` reusing `frontend/src/features/backtest/` panels
- [X] T027 [US2] Default-hide comparison-originated runs in `frontend/src/features/backtest/BacktestRunList.tsx` / `useBacktest.ts`; add control to include them
- [X] T028 [US2] Implement `GET /comparisons` and `GET /comparisons/{id}` in `backend/app/api/comparison.py` for re-open/inspect of stored comparisons
- [X] T029 [US2] Run T022–T023; fix until passing

**Checkpoint**: Drill-down and history filtering satisfy FR-007 / SC-004

---

## Phase 5: User Story 3 - Per-strategy parameters under shared market assumptions (Priority: P2)

**Goal**: Each leg has its own strategy id + params via dynamic `StrategyConfigFields`; invalid params on any leg reject before run.

**Independent Test**: Select RSI + Dual EMA with distinct valid params; completed legs show matching `strategyParams`; bad RSI thresholds → 400 with constraint message.

### Tests for User Story 3

- [X] T030 [P] [US3] Contract test: per-leg effective params persisted; one invalid leg rejects whole create in `backend/tests/contract/test_comparison_api.py` (extend)
- [X] T031 [P] [US3] Frontend tests: editing one leg’s params does not change another; client validation surfaces strategy constraint in `frontend/src/__tests__/comparisonParams.test.tsx`

### Implementation for User Story 3

- [X] T032 [US3] Multi-leg editor: add/remove legs (clamp 2–5), each with `StrategyConfigFields`, in `frontend/src/features/comparison/` 
- [X] T033 [US3] Ensure orchestrator validates each leg via `validate_and_materialize` independently in `backend/app/comparison/service.py` (FR-004)
- [X] T034 [US3] Allow duplicate `strategyId` across legs with different params (contract + UI) per FR-002
- [X] T035 [US3] Run T030–T031; fix until passing

**Checkpoint**: Per-leg configuration works without shared-param forcing

---

## Phase 6: User Story 4 - Optional common risk limits (Priority: P2)

**Goal**: Optional Feature 004 risk inputs (e.g. `maxTrades`, profit/loss rates) set once on the comparison and applied identically to every leg.

**Independent Test**: Same two strategies with and without `maxTrades`; when set, both legs honor the same cap.

### Tests for User Story 4

- [X] T036 [P] [US4] Contract/integration test: omitted limits do not apply; set `maxTrades` applies to all legs in `backend/tests/contract/test_comparison_api.py` and/or `backend/tests/integration/test_comparison_shared_candles.py` (extend)

### Implementation for User Story 4

- [X] T037 [US4] Accept optional common risk fields on comparison create body and pass through to each leg `run_engine` call in `backend/app/comparison/service.py` / `backend/app/api/comparison.py`
- [X] T038 [US4] Expose optional common risk inputs on comparison form in `frontend/src/features/comparison/` (align with `BacktestConfigForm` optional fields)
- [X] T039 [US4] Run T036; fix until passing

**Checkpoint**: Shared optional risk limits keep comparisons fair

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Retention UX, delete semantics, docs, regression, quickstart green

- [X] T040 [P] Implement `DELETE /comparisons/{id}` without cascading leg backtest deletion in `backend/app/api/comparison.py` / `backend/app/comparison/repository.py`
- [X] T041 [P] Assert comparison responses never include winner/best fields in `backend/tests/contract/test_comparison_api.py` (FR-008 / SC-006)
- [X] T042 [P] Document Feature 007 in root `README.md` (link to `specs/007-strategy-comparison/quickstart.md`)
- [X] T043 Re-run Dual EMA continuity: `pytest backend/tests/unit/test_dual_ema_continuity.py -q`
- [X] T044 Run quickstart.md automated checks (comparison unit/contract/integration + frontend comparison tests) and fix remaining failures
- [X] T045 [P] Vite proxy / frontend env: ensure `/comparisons` is proxied like `/backtest` if required by `frontend` Vite config

**Checkpoint**: Feature complete — fair sync comparison, inspectable filtered legs, retention, docs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Stories (Phases 3–6)**: All depend on Foundational
  - US1 (comparison run) is **MVP** — prefer first
  - US2 (inspect/filter) builds on US1 persisted `backtestRunId`s — after or tightly with US1
  - US3 (per-leg params) and US4 (common risk) extend US1 create path; can follow US1
- **Polish (Phase 7)**: Depends on US1–US4 complete enough for quickstart

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — MVP
- **US2 (P1)**: After US1 create persists legs (needs `backtestRunId` + origin)
- **US3 (P2)**: After Phase 2; ideally after US1 form exists
- **US4 (P2)**: After Phase 2; extends shared create body from US1

### Within Each User Story

- Tests (where listed) should fail before implementation where practical
- Backend orchestrator/API before frontend wiring when the same story owns both
- Do not fork Feature 004 engine or strategy modules

### Parallel Opportunities

- T002 with T003; T004 then T005 sequential on `models.py` (T005 is not `[P]`)
- T010 with T011 after repository/filter exist
- Within US1: T013–T015 [P]; T018 [P] with backend T016–T017 once contract stable
- US3/US4 test tasks [P] after their API shapes exist
- Phase 7: T040, T041, T042, T045 [P]

---

## Parallel Example: User Story 1 (MVP)

```bash
# After Phase 2:
Task: "Unit tests in backend/tests/unit/test_comparison_orchestrator.py"
Task: "Contract tests in backend/tests/contract/test_comparison_api.py"
Task: "Integration shared candles in backend/tests/integration/test_comparison_shared_candles.py"

# After orchestrator + POST land:
Task: "comparisonApi.ts client"
Task: "Frontend comparison form/results + AutoTradingPage host"
Task: "Frontend comparison.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schema, origin filter, helpers)
3. Complete Phase 3: US1 sync comparison API + basic UI
4. **STOP and VALIDATE**: Two-strategy comparison completes with required metrics
5. Demo MVP

### Incremental Delivery

1. Setup + Foundational → schema/helpers
2. US1 → sync comparison MVP
3. US2 → inspect + history filter
4. US3 → per-leg params UX
5. US4 → optional common risk limits
6. Polish → retention delete, docs, quickstart green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Phase 2:
   - Dev A: US1 backend orchestrator/API
   - Dev B: US1 frontend form/table
   - Dev C: US2 history filter + inspect wiring (after leg ids exist)
3. US3/US4 extend create path carefully
4. One owner runs Phase 7 polish

---

## Notes

- [P] = different files, no incomplete dependencies
- [Story] maps to US1–US4 for traceability
- Prefer sequential edits when multiple tasks touch `backend/app/db/models.py` or `AutoTradingPage.tsx`
- Do **not** implement optimization, ranking badges, async comparison jobs, or real money
- Each story independently testable once its phase completes
- Stop at any checkpoint to validate without waiting for later stories
