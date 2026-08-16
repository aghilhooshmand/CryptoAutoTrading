# Tasks: Live Paper-Trading Hardening

**Input**: Design documents from `/specs/014-live-paper-trading-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required — FR-020 / SC-001–SC-008 (startup recover-and-reconcile,
`RECOVERY_BLOCKED`, duplicate candle/event non-replay, offline gap skip + audit,
reconciliation pass/fail gates, resume re-gates, stale/unavailable mark
fail-closed, bounded public retry without duplicate trades, emergency stop under
degradation, operator-visible interrupted/degraded signals). Prefer fixtures /
mocks; no multi-hour live CI; no XT private credentials required.

**Analyze remediations** (2026-08-16): C1/A1 full FR-006 G1–G5 before any
auto-resume (T014); I1 gap-skip before `RUNNING` in US1 (T015–T016); U1
`init_db` `_ensure_column` / indexes (T004–T006); U2 concrete FR-011 path
(T035); D1 merged gap-skip wiring into US1; U3 fill/journal/watermark atomicity
(T021); A2 public retry helper at `public_retry.py` (T033–T034); I2 spec US4
independent-test wording; G1 hard-stop regression (T047). Header IDs aligned
with post-renumber tasks (re-analyze L1).

**Organization**: Extend existing Simulation + public `market_data` only. Propose
commits only; do not auto-commit. Keep Feature 014 `IN PROGRESS` on
`docs/ROADMAP.md` until acceptance; mark `DONE` only in polish after gates.

**Spec locks** (must hold through all tasks):
- Single pipeline; no second paper-trading engine (FR-001, FR-002)
- Never invent prices, fills, decisions, or Portfolio balances (FR-003)
- Conditional safe auto-recovery only after **all** FR-006 gates **and** FR-010
  gap-skip success; else `RECOVERY_BLOCKED` (FR-005, FR-007, FR-010)
- Skip offline closed candles; advance watermark; audit gap; no gap fills (FR-010)
- Public retries: max **1**; default backoff **0.5s**; Retry-After cap **2.0s** (FR-012 / research R5)
- Stale-while-long: block entries; `UNSAFE_QUOTE_LIMIT=3`; flatten only with safe mark else `unsafe_unflattened` (FR-011)
- Simulation Portfolio only; Real XT unused for paper fills (FR-018)
- RealExecutionAdapter stays unavailable; no private trading APIs (FR-019)
- `STOPPED` remains History-terminal; resume only from `RECOVERY_BLOCKED` (data-model)
- No 4th primary nav; UI ~375px (FR-016, constitution XIII–XIV)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US5 map to spec stories

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/014-live-paper-trading-hardening/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

**Purpose**: Align docs and confirm touch points; no behavior change yet

- [x] T001 Verify Feature 014 is `IN PROGRESS` on `docs/ROADMAP.md` and branch is `014-live-paper-trading-hardening`; note replace target `backend/app/simulation/recovery.py` (orphan→STOPPED baseline)
- [x] T002 [P] Add brief Feature 014 recovery/resume notes to `README.md` (operator: conditional auto-resume only after full reconcile + gap skip vs `RECOVERY_BLOCKED`; no Real trading) without inventing undocumented API details

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Lifecycle, schema, and shared reconcile/gap types required by all stories

**⚠️ CRITICAL**: No user-story recovery/resume/UI until this phase completes

- [x] T003 Extend session state machine with `RECOVERY_BLOCKED` transitions in `backend/app/simulation/state_machine.py` (`allows_strategy_execution` remains `RUNNING` only; `STOPPED` stays terminal; document legal transitions per `data-model.md`)
- [x] T004 Extend `SimulationSessionRow` in `backend/app/db/models.py` with `recovery_reason`, `recovery_detail`, `last_recovery_at` (nullable) and ensure state accepts `RECOVERY_BLOCKED`; add matching `_ensure_column` calls in `backend/app/db/session.py` `init_db()` (SQLite `create_all` does not alter existing tables)
- [x] T005 [P] Add `SkippedGapAudit` model/table in `backend/app/db/models.py` per `data-model.md`; ensure table is created via `init_db()` / `create_all` in `backend/app/db/session.py`
- [x] T006 [P] Add trade/decision journal uniqueness in `backend/app/db/models.py` per research R4 (`(session_id, candle_open_time, is_forced_close)` for trades; `(session_id, candle_open_time)` for decisions); bootstrap unique indexes for existing SQLite DBs in `backend/app/db/session.py` `init_db()` (not only `create_all`)
- [x] T007 Implement `ReconcileResult` + stable gate/recovery codes in `backend/app/simulation/reconcile.py` (shell: codes from `contracts/simulation-recovery-api.md`; fail-closed default; no invent)
- [x] T008 [P] Extend `session_to_dict` / API session payload in `backend/app/simulation/session_service.py` with camelCase `recoveryReason`, `recoveryDetail`, `lastRecoveryAt`, optional `skippedGap` per `contracts/simulation-recovery-api.md`
- [x] T009 [P] Extend unit tests for new transitions in `backend/tests/unit/test_state_machine.py` (illegal transitions; strategy execution only in `RUNNING`)
- [x] T010 Treat `RECOVERY_BLOCKED` as occupying the single active slot in `backend/app/simulation/session_service.py` (block second start while blocked; include in active-session queries)

**Checkpoint**: Schema + state machine + reconcile shell ready; recovery behavior still baseline until US1

---

## Phase 3: User Story 1 - Survive backend restart without unsafe trading (Priority: P1) 🎯 MVP

**Goal**: On backend restart, orphaned Simulations run **full** FR-006 reconciliation and FR-010 gap-skip; only then may auto-resume to `RUNNING`; otherwise non-trading `RECOVERY_BLOCKED` with zero invented fills.

**Independent Test**: Fixture orphan `RUNNING`/`STOPPING` → `RUNNING` only if G1–G5 pass **and** gap-skip succeeds (watermark advanced / audit when gap exists); else `RECOVERY_BLOCKED`; no invented prices/fills; worker does not trade while blocked.

### Tests

- [x] T011 [P] [US1] Unit tests in `backend/tests/unit/test_recovery_014.py` for recover-and-reconcile (all-gates pass + gap-skip → `RUNNING`; any gate/gap fail → `RECOVERY_BLOCKED`; no invent) updating orphan→STOPPED-only expectations in `backend/tests/unit/test_recovery.py`
- [x] T012 [P] [US1] Unit tests in `backend/tests/unit/test_gap_skip.py` for skip-advance, audit persistence, and `recovery_gap_unresolvable` when history missing (required before US1 auto-resume)
- [x] T013 [P] [US1] Assert worker never strategy-executes `RECOVERY_BLOCKED` in `backend/tests/unit/test_recovery_014.py` or `backend/tests/unit/test_state_machine.py`

### Implementation

- [x] T014 [US1] Implement **all** FR-006 gates G1–G5 in `backend/app/simulation/reconcile.py` (session↔journals, watermark↔journals, Portfolio binding/holdings, no `unsafe_unflattened`, trustworthy mark when long). **MUST** be complete before any auto-resume path; no partial-gate resume; no invented corrections
- [x] T015 [US1] Implement offline gap skip + watermark advance + audit write in `backend/app/simulation/gap_skip.py` (FR-010)
- [x] T016 [US1] Replace orphan→STOPPED-only logic in `backend/app/simulation/recovery.py`: run G1–G5; on pass run gap-skip; **only then** set `RUNNING` (clear recovery fields); on any gate or gap failure set `RECOVERY_BLOCKED` + reason/detail; never invent marks/fills; keep lifespan hook in `backend/app/main.py`
- [x] T017 [US1] Ensure `backend/app/simulation/worker.py` only ticks `RUNNING` sessions (explicitly skip `RECOVERY_BLOCKED` / `STOPPING`)
- [x] T018 [US1] Run US1 gates until green: `backend/tests/unit/test_recovery_014.py`, `backend/tests/unit/test_gap_skip.py`, updated `backend/tests/unit/test_recovery.py`, `backend/tests/unit/test_state_machine.py`

**Checkpoint**: MVP restart safety — full gates + gap-skip before auto-resume, else `RECOVERY_BLOCKED`

---

## Phase 4: User Story 2 - Prevent duplicate trades after restart or retry (Priority: P1)

**Goal**: Pipeline/journal idempotency so restart or retry cannot double-fill; atomic fill→Portfolio→journals→watermark ordering; gap-skip already required in US1 recovery.

**Independent Test**: Re-present processed candle → zero second fill; mid-fill crash fixture (journal ahead of watermark or Portfolio lag) fails closed on reconcile; HOLD still advances watermark without duplicate fills.

### Tests

- [x] T019 [P] [US2] Unit/pipeline tests asserting duplicate candle / `last_processed_candle_open_time` replay creates no second fill in `backend/tests/unit/` (extend pipeline tests or `test_gap_skip.py` companions)
- [x] T020 [P] [US2] Unit test for mid-fill / ordering mismatch (journal vs watermark vs Portfolio) → reconcile fail / `RECOVERY_BLOCKED` in `backend/tests/unit/test_reconcile.py` or `backend/tests/unit/test_recovery_014.py`

### Implementation

- [x] T021 [US2] Harden idempotent candle handling **and** transactional ordering in `backend/app/simulation/pipeline.py`: refuse fill if watermark ≥ candle or trade journal already has event; within one DB transaction apply fill + Portfolio + journals then watermark (research R4); preserve HOLD watermark advance
- [x] T022 [US2] Run US2 gates until green: duplicate-candle and ordering-mismatch tests under `backend/tests/unit/`

**Checkpoint**: No duplicate fills; crash mid-fill fails closed

---

## Phase 5: User Story 3 - Reconcile before any post-recovery trading (Priority: P1)

**Goal**: Operator `POST .../resume` re-runs full G1–G5 + gap-skip; stop/close from `RECOVERY_BLOCKED`; gate failure codes covered by contract tests (gates already implemented in US1).

**Independent Test**: Mismatch fixtures → `RECOVERY_BLOCKED` + stable codes; resume success only when all gates + gap-skip pass; `STOPPED` resume → `invalid_state_for_resume`.

### Tests

- [x] T023 [P] [US3] Unit tests in `backend/tests/unit/test_reconcile.py` covering G1–G5 pass/fail codes (`reconcile_session_journal_mismatch`, `reconcile_watermark_inconsistent`, `reconcile_portfolio_mismatch`, `reconcile_unsafe_unflattened`, `reconcile_mark_untrustworthy`)
- [x] T024 [P] [US3] Contract tests in `backend/tests/contract/test_simulation_resume_api.py` for `POST /simulation/sessions/{id}/resume` success/409 shapes per `contracts/simulation-recovery-api.md`

### Implementation

- [x] T025 [US3] Harden `backend/app/simulation/reconcile.py` for resume edge cases without weakening US1 gates: (1) unbound session that is long while Portfolio still shows a projected holding → `reconcile_portfolio_mismatch`; (2) watermark null with existing trade journal rows → `reconcile_watermark_inconsistent`; cover both in `backend/tests/unit/test_reconcile.py` — no invented corrections
- [x] T026 [US3] Implement `resume_session` in `backend/app/simulation/session_service.py` (`RECOVERY_BLOCKED` only → re-run G1–G5 → gap-skip → `RUNNING` or remain blocked)
- [x] T027 [US3] Add `POST /simulation/sessions/{id}/resume` in `backend/app/api/simulation.py` with error envelope codes from contract
- [x] T028 [US3] Allow stop / emergency-stop from `RECOVERY_BLOCKED` via `STOPPING`→`STOPPED` in `backend/app/simulation/session_service.py` (flatten only with safe mark else `unsafe_unflattened`)
- [x] T029 [US3] Ensure `GET /simulation/sessions/active` includes `RECOVERY_BLOCKED` occupying session in `backend/app/api/simulation.py` / session queries
- [x] T030 [US3] Run US3 gates until green: `backend/tests/unit/test_reconcile.py`, `backend/tests/contract/test_simulation_resume_api.py`

**Checkpoint**: Resume/stop operator paths on top of full gates

---

## Phase 6: User Story 4 - Stale data and temporary public market failures (Priority: P1)

**Goal**: Bounded public retries; stale/unavailable marks never invent exits; while long, block entries and use unsafe-mark streak; on exhaustion stop strategy trading with safe flatten or `unsafe_unflattened`.

**Independent Test**: Retry fixture exhausts after one retry within bounds; unsafe mark while long blocks entries; streak exhaustion → stop without invented exit price.

### Tests

- [x] T031 [P] [US4] Unit tests in `backend/tests/unit/test_public_market_retry.py` for max 1 retry, 0.5s default backoff, Retry-After cap 2.0s, no retry when wait would exceed cap (per `contracts/public-market-retry.md`)
- [x] T032 [P] [US4] Tests for stale-while-long / `UNSAFE_QUOTE_LIMIT` in `backend/tests/unit/`: (a) first unsafe mark while long blocks new entries; (b) streak reaches 3 → stop strategy trading; (c) flatten only if safe mark else `unsafe_unflattened` with no invented price

### Implementation

- [x] T033 [US4] Add dedicated bounded public retry helper in `backend/app/market_data/public_retry.py` (max 1 retry; 0.5s default; Retry-After ≤2.0s) per research R5 — reads only; no private client
- [x] T034 [US4] Wire Simulation mark/candle/gap-history fetches through `backend/app/market_data/public_retry.py` from `backend/app/simulation/pipeline.py` and `backend/app/simulation/gap_skip.py` (keep adapter thin; do not bypass watermark idempotency)
- [x] T035 [US4] Implement FR-011 in `backend/app/simulation/pipeline.py` and `backend/app/simulation/control/risk.py`: on untrustworthy mark while `position_side == long`, block new strategy-driven entries immediately; increment `unsafe_quote_streak`; keep `UNSAFE_QUOTE_LIMIT = 3`; on exhaustion call stop path that flattens only when mark is trustworthy else set `position_flatten_status = unsafe_unflattened` with no invented exit price
- [x] T036 [US4] Run US4 gates until green: `backend/tests/unit/test_public_market_retry.py` and stale-while-long tests from T032

**Checkpoint**: Public retry bounds + stale-while-long fail-closed

---

## Phase 7: User Story 5 - Operate and observe long-running / degraded sessions (Priority: P2)

**Goal**: Operators see `RECOVERY_BLOCKED` vs `STOPPED`, recovery reasons, skipped-gap summary; Resume/Stop/Emergency stop work; usable at ~375px; structured diagnostics without secrets.

**Independent Test**: UI/API shows blocked state distinct from normal stop; emergency stop during degradation prevents new entries; ~375px layout remains operable.

### Tests

- [x] T037 [P] [US5] Frontend tests for `RECOVERY_BLOCKED` status + Resume control in `frontend/src/` (e.g. `SessionStatusPanel` / simulation feature tests)
- [x] T038 [P] [US5] Contract or unit assert emergency stop from `RECOVERY_BLOCKED` / degraded `RUNNING` prevents strategy entries in `backend/tests/contract/test_simulation_resume_api.py` or session service tests

### Implementation

- [x] T039 [US5] Add `resumeSession` to `frontend/src/services/simulationApi.ts`
- [x] T040 [US5] Update `frontend/src/features/simulation/SessionStatusPanel.tsx` to show `RECOVERY_BLOCKED`, `recoveryReason` / detail, `skippedGap`, Resume + Stop/Emergency controls; distinguish from normal `STOPPED`
- [x] T041 [US5] Update `frontend/src/features/simulation/useSimulationSession.ts` and history list filters in `frontend/src/features/simulation/SimulationHistoryList.tsx` for `RECOVERY_BLOCKED`
- [x] T042 [US5] Ensure degraded/recovery UI meets `docs/UI_UX_STANDARDS.md` and remains usable at ~375px width (no 4th primary nav)
- [x] T043 [US5] Add structured recovery/reconcile logging (session id, outcome, gate codes; no secrets) in `backend/app/simulation/recovery.py` / `reconcile.py`
- [x] T044 [US5] Run US5 gates until green: frontend recovery UI tests under `frontend/` and emergency-stop cases in `backend/tests/contract/test_simulation_resume_api.py` / session service tests

**Checkpoint**: Operator-visible recovery/degraded states

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Safety regressions, docs, ROADMAP, quickstart alignment

- [x] T045 [P] Assert RealExecutionAdapter remains unavailable and Feature 014 adds no XT private trading calls in `backend/tests/unit/test_real_execution_stub.py` (or thin companion test)
- [x] T046 [P] Assert Simulation Portfolio isolation from Real XT during recovery paths in `backend/tests/unit/` (no Real XT merge)
- [x] T047 [P] Add regression assert that existing session hard-stops (emergency stop / max-loss / duration controls as applicable) still prevent new entries after Feature 014 changes in `backend/tests/unit/` or contract tests (FR-015)
- [x] T048 [P] Update `specs/014-live-paper-trading-hardening/quickstart.md` if commands/paths drifted during implement
- [x] T049 Run full Feature 014 pytest set from `specs/014-live-paper-trading-hardening/quickstart.md` until green (`backend/tests/unit/test_reconcile.py`, `test_recovery_014.py`, `test_gap_skip.py`, `test_public_market_retry.py`, `test_state_machine.py`, `backend/tests/contract/test_simulation_resume_api.py`)
- [x] T050 Mark Feature 014 `DONE` on `docs/ROADMAP.md` only after acceptance gates; leave commit proposal to operator (no auto-commit)

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1** → **Phase 2** → stories
- **US1 (P1) MVP**: full G1–G5 + gap-skip + recover-and-reconcile (no partial auto-resume)
- **US2**: pipeline idempotency + atomicity (after US1 recovery exists)
- **US3**: resume/stop API on top of US1 gates + US1 gap-skip
- **US4**: after foundational; wire retries after US2 idempotency preferred
- **US5**: after US3 resume/status fields
- **Polish** after US1–US5

### User story dependency graph

```text
Phase 2 Foundational
    └── US1 Restart recovery (MVP: G1–G5 + gap-skip + RECOVERY_BLOCKED)
          ├── US2 Dedupe + atomic pipeline
          ├── US3 Resume API + stop from RECOVERY_BLOCKED
          ├── US4 Stale + public retry
          └── US5 Operator UI ──► Phase 8 Polish
```

### Parallel opportunities

- Within Phase 2: T005–T006, T008–T009 [P]
- Within US1: T011–T013 tests [P]
- Within US2: T019–T020 tests [P]
- Within US3: T023–T024 tests [P]
- Within US4: T031–T032 tests [P]
- Within US5: T037–T038 tests [P]
- Polish T045–T048 [P]

### Independent test criteria (per story)

| Story | Independent test |
|-------|------------------|
| US1 | Restart → `RUNNING` only after G1–G5 + gap-skip; else `RECOVERY_BLOCKED` |
| US2 | Duplicate candle → 0 second fill; ordering mismatch fails closed |
| US3 | Resume only when gates + gap-skip pass; stop from blocked |
| US4 | Retry bounds; stale long → no invented exit |
| US5 | UI shows `RECOVERY_BLOCKED`; emergency stop works; ~375px |

### Suggested MVP

**US1 only** (Phase 1–3): full reconcile gates + gap-skip + conditional auto-resume / `RECOVERY_BLOCKED`. Then US2 → US3 → US4 → US5 → Polish.

---

## Implementation Strategy

1. Land foundational state/schema + `init_db` column/index bootstrap.
2. Ship US1 MVP with **complete** G1–G5 and gap-skip before any `RUNNING` resume.
3. Harden pipeline idempotency/atomicity (US2), then resume API (US3).
4. Public retries + stale path (US4), then operator UI (US5).
5. Polish regressions (incl. FR-015) and ROADMAP `DONE`.

**Format validation**: All tasks use `- [ ]`, sequential `T00N` IDs, optional `[P]`, story labels on US phases only, and include explicit file paths.

---

## Phase 9: Convergence

**Purpose**: Close gaps found by `/speckit-converge` (2026-08-16) between Feature 014 artifacts and the current codebase. Run via `/speckit-implement`.

- [x] T051 Fail closed in `backend/app/simulation/gap_skip.py` when `last_processed_candle_open_time` is set and closed-candle history is empty (successful empty fetch or equivalent): return `recovery_gap_unresolvable` instead of passing — per FR-010 / research R4 (`contradicts`)
- [x] T052 [P] Extend G3 in `backend/app/simulation/reconcile.py` so unbound **flat** sessions fail `reconcile_portfolio_mismatch` when Portfolio still has a non-zero base holding for the session symbol (projection conflict); add coverage in `backend/tests/unit/test_reconcile.py` — per FR-006c / plan R3 / T025 intent (`partial`)
- [x] T053 [P] Add FR-011 stale-while-long unit tests in `backend/tests/unit/` (first unsafe mark while long blocks entries; streak reaches `UNSAFE_QUOTE_LIMIT` → stop; flatten only with safe mark else `unsafe_unflattened`) — per FR-011 / FR-020 / T032 (`missing`)
- [x] T054 [P] Add simulation duplicate-candle non-replay fill test in `backend/tests/unit/` or `backend/tests/integration/test_simulation_pipeline.py` asserting watermark/journal idempotency prevents a second fill — per FR-008 / FR-020 / T019 (`missing`)
- [x] T055 [P] Add FR-015 hard-stop regression tests in `backend/tests/unit/test_014_safety_gates.py` (or companion) asserting emergency stop / max-loss / duration still prevent new strategy entries after Feature 014 changes — per FR-015 / T047 (`missing`)
- [x] T056 [P] Add ~375px usability smoke for recovery UI (`RECOVERY_BLOCKED` / Resume) in `frontend/src/__tests__/` following existing `simulationResponsive.test.tsx` patterns — per FR-016 / T042 (`partial`)
- [x] T057 Set Feature 014 `spec.md` **Status** from Draft to an implemented/complete label consistent with ROADMAP DONE after T051–T056 pass — per process/docs alignment (`partial`)
