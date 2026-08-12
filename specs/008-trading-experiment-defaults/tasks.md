# Tasks: Trading & Experiment Defaults

**Input**: Design documents from `/specs/008-trading-experiment-defaults/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context, constitution XXVIII, and quickstart require settings unit/contract tests plus frontend Settings and create-form seed coverage.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Spec precedence** (Session 2026-08-12 clarifications + plan/research):
- SQLite singleton Settings + `GET` / `PUT` / `POST /settings/reset` (not `localStorage` source of truth)
- Explicit **Save**; unsaved draft does not seed create forms; unsaved Settings draft survives Auto Trading tab switches until Save/Reset/full reload
- Fail-closed `GET /settings` `warning` MUST be shown in Settings UI (FR-014)
- Explicit **Reset** persists product starters; no trading side effects
- Apply Settings on **fresh form open only**; never overwrite in-progress drafts
- Comparison: seed **first leg only** from preferred strategy; other legs = product/registry starters
- Preferred strategy change in Settings draft → **reset params** to registry defaults
- One product-starter set: capital `1000` nesting; optional risk unset; `dual_ema` + registry defaults
- Simulation: unset optional risk in Settings → leave empty; keep Simulation’s own required validation at create/start
- Settings under Auto Trading tab only (no 4th primary nav)
- Defaults never rewrite historical effective configs
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/008-trading-experiment-defaults/`, `docs/ROADMAP.md`, root `README.md` only if needed

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm touch points; create Settings package/UI stubs

- [X] T001 Verify create-form and registry paths exist (`frontend/src/features/simulation/SessionConfigForm.tsx`, `frontend/src/features/backtest/BacktestConfigForm.tsx`, `frontend/src/features/comparison/ComparisonConfigForm.tsx`, `frontend/src/features/strategy/StrategyConfigFields.tsx`, `backend/app/strategy/registry.py`, `backend/app/simulation/session_service.py`, `frontend/src/pages/AutoTradingPage.tsx`) per plan.md
- [X] T002 [P] Create package layout `backend/app/settings/` (`__init__.py`) and confirm `backend/tests/unit/`, `backend/tests/contract/` ready for settings test files
- [X] T003 [P] Create frontend stubs `frontend/src/features/settings/` and `frontend/src/services/settingsApi.ts` (types/placeholder exports only) per plan.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Singleton persistence, product starters, validation service, read API, proxy — blocks all user stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T004 Add `OperatorDefaultsRow` (or equivalent singleton) in `backend/app/db/models.py` and ensure `init_db` / light migration creates the table per `data-model.md`
- [X] T005 [P] Define `ProductStarterDefaults` constants in `backend/app/settings/starters.py` (symbol `btc_usdt`, timeframe `1h`, capital `1000`/`1000`/`1000`, fee `0.002`, slippage `0.0005`, optional risk unset, `dual_ema` + registry defaults) per research Decision 3
- [X] T006 Implement singleton load/save in `backend/app/settings/repository.py` (overwrite on save; no Settings version history)
- [X] T007 Implement Settings domain validation + load/save/reset orchestration in `backend/app/settings/service.py` (reuse capital nesting + `validate_and_materialize`; corrupt/invalid stored payload fail-closed to starters with warning; **never** call simulation/backtest/comparison start/stop) per research Decisions 7–8
- [X] T008 Implement `GET /settings` and mount router in `backend/app/api/settings.py` and `backend/app/main.py` per `contracts/operator-defaults-api.md` (`source: starters|saved`; no mutate on GET)
- [X] T009 [P] Add Vite proxy `/settings` → backend in `frontend/vite.config.ts` (alongside `/comparisons`)
- [X] T010 [P] Unit tests: starters shape, corrupt fail-closed, Save does not invoke trading services in `backend/tests/unit/test_settings_service.py`
- [X] T011 [P] Contract tests: empty DB `GET /settings` returns starters with `source=starters` in `backend/tests/contract/test_settings_api.py`
- [X] T012 Run baseline create-API smoke: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py backend/tests/contract/test_comparison_api.py -q` must pass before Settings UI/form wiring

**Checkpoint**: Read path + persistence foundation ready; user stories can build Save UI, form seeding, history proofs, Reset

---

## Phase 3: User Story 1 - Save reusable trading defaults (Priority: P1) 🎯 MVP

**Goal**: Operator can open Settings under Auto Trading, edit registry-driven defaults, explicitly Save, and reload the same values on the same machine.

**Independent Test**: Open Settings, save a valid distinctive set, leave and return → same values; unsaved edits do not become active defaults and survive Auto Trading tab switches until Save/Reset/reload; strategy params follow registry schema; switching preferred strategy resets params to that strategy’s registry defaults in the draft; fail-closed `warning` from GET is shown in the UI.

### Tests for User Story 1

- [X] T013 [P] [US1] Contract tests for `PUT /settings`: valid save returns `source=saved` + `updatedAt`; invalid nesting/params leave prior row unchanged in `backend/tests/contract/test_settings_api.py` (extend)
- [X] T014 [P] [US1] Frontend tests in `frontend/src/__tests__/settings.test.tsx`: Settings tab Save round-trip; unsaved draft not treated as active for forms; unsaved draft survives simulated Auto Trading tab leave/return; strategy change resets params; when mocked `GET /settings` includes a non-null `warning`, the Settings UI shows that warning
- [X] T015 [US1] Implement `PUT /settings` in `backend/app/api/settings.py` (+ service) per `contracts/operator-defaults-api.md` (explicit Save; domain validation; no trading side effects)
- [X] T016 [P] [US1] Implement `getSettings` / `putSettings` client in `frontend/src/services/settingsApi.ts`
- [X] T017 [US1] Build Settings form (market, capital nesting, costs, optional risk, preferred strategy via `StrategyConfigFields`) with explicit Save in `frontend/src/features/settings/` and add Settings tab on `frontend/src/pages/AutoTradingPage.tsx` (no 4th primary nav); preserve unsaved draft across Auto Trading tab switches (no auto-save/auto-discard); display `GET /settings` `warning` when present per FR-001–FR-003 / FR-006 / FR-010–FR-011 / FR-014
- [X] T018 [US1] On preferred-strategy change in Settings draft, reset params to registry defaults before Save in `frontend/src/features/settings/` (reuse `StrategyConfigFields` / `defaultParamsFor` behavior) per FR-003 / clarify Q4
- [X] T019 [US1] Run T010–T014; fix until passing

**Checkpoint**: MVP — Settings can be saved and reloaded under Auto Trading

---

## Phase 4: User Story 2 - New configurations start from Settings (Priority: P1)

**Goal**: Fresh Simulation, Backtest, and Comparison create forms initialize from last successfully saved Settings (comparison: shared fields + first leg only); in-progress drafts are never overwritten; Simulation leaves unset optional risk empty and keeps its own required validation.

**Independent Test**: Save distinctive Settings; open each fresh create form → fields match; override one field and create without changing Settings; mid-edit draft survives Settings changes elsewhere; unset risk in Settings → Simulation fields empty + create validation still applies.

### Tests for User Story 2

- [X] T020 [P] [US2] Frontend tests: fresh Simulation/Backtest/Comparison init from mocked Settings; comparison leg0 only; draft not overwritten on Settings change; Simulation empty optional risk when unset in `frontend/src/__tests__/settingsFormInit.test.tsx` (and/or extend existing config form tests)

### Implementation for User Story 2

- [X] T021 [US2] Add shared helper to map Settings body → create-form initial values in `frontend/src/features/settings/` (or `frontend/src/features/shared/`) per FR-004 / FR-013
- [X] T022 [US2] Wire `SessionConfigForm.tsx` to initialize from `GET /settings` on **fresh** open / post-create reset only (replace hard-coded 500 starters when Settings apply; leave unset optional risk empty; keep Simulation required validation at submit) in `frontend/src/features/simulation/SessionConfigForm.tsx`
- [X] T023 [P] [US2] Wire `BacktestConfigForm.tsx` fresh init from Settings (shared market/money/cost/optional risk + strategy) in `frontend/src/features/backtest/BacktestConfigForm.tsx`
- [X] T024 [P] [US2] Wire `ComparisonConfigForm.tsx` fresh init: shared fields from Settings; **leg 0** = preferred strategy/params; **leg 1+** = product/registry starters in `frontend/src/features/comparison/ComparisonConfigForm.tsx` per clarify Q1
- [X] T025 [US2] Ensure create forms do not re-apply Settings while an in-progress draft is active (tab leave/return without discard) in the three config forms / hooks per clarify Q2 / FR-004
- [X] T026 [US2] Ensure create forms read **saved** Settings only (not unsaved Settings UI draft) — e.g. refetch `GET /settings` on fresh open — in form wiring + `frontend/src/services/settingsApi.ts` per FR-006
- [X] T027 [US2] Run T020; fix until passing

**Checkpoint**: SC-001 / SC-002 — fresh forms prefill from saved Settings

---

## Phase 5: User Story 3 - Defaults never rewrite history (Priority: P1)

**Goal**: Changing Settings after sessions/runs/comparisons exist leaves those artifacts’ effective configurations unchanged; only new creates use updated Settings.

**Independent Test**: Create a backtest (or simulation) with known effective values; change Settings; reopen historical artifact → original config unchanged; new create form uses updated Settings.

### Tests for User Story 3

- [X] T028 [P] [US3] Contract/integration test: create backtest (or simulation) → `PUT /settings` with different fee/capital → `GET` historical artifact still shows original effective config in `backend/tests/contract/test_settings_history_immunity.py` (or extend existing contract files)
- [X] T029 [P] [US3] Frontend or API-level assertion that Settings Save/Reset paths never call create/start session/run/comparison endpoints in `frontend/src/__tests__/settingsNoTradingSideEffects.test.tsx` and/or backend unit spies in `backend/tests/unit/test_settings_service.py` (extend)

### Implementation for User Story 3

- [X] T030 [US3] Verify Settings service and API have **no** FK updates to `simulation_sessions` / `backtest_runs` / comparison tables; document invariant in `backend/app/settings/service.py` (code comment or module docstring) per FR-005 / FR-008
- [X] T031 [US3] Confirm create services continue to persist effective config from request body only (no live Settings lookup after create) in `backend/app/simulation/session_service.py`, `backend/app/backtest/service.py`, `backend/app/comparison/service.py` — fix only if a Settings read was accidentally introduced
- [X] T032 [US3] Run T028–T029; fix until passing

**Checkpoint**: SC-003 — Settings changes cannot rewrite history

---

## Phase 6: User Story 4 - Validate and reset Settings safely (Priority: P2)

**Goal**: Invalid Settings Save is rejected with clear reasons and last good Settings remain active; Reset restores product starters (persisted) without starting/stopping trading; optional blanks stay unset.

**Independent Test**: Bad capital nesting → Save rejected, prior Settings still seed forms; blank optionals save as unset; Reset → starters active; no trading activity started.

### Tests for User Story 4

- [X] T033 [P] [US4] Contract tests: invalid nesting / invalid strategy params → `400` + prior row unchanged; optional nulls persist as unset; `POST /settings/reset` returns starters and does not create sessions/runs in `backend/tests/contract/test_settings_api.py` (extend)
- [X] T034 [P] [US4] Frontend tests in `frontend/src/__tests__/settings.test.tsx` (extend): Save error surfaces clear message; Reset confirmation restores starters without trading calls; at ~375px viewport width, Save and Reset remain visible/usable without hover-only controls (SC-006)
- [X] T035 [US4] Ensure `PUT /settings` maps validation failures to existing error codes/messages (`invalid_config`, `unknown_strategy`, `invalid_strategy_params`) in `backend/app/api/settings.py` / `backend/app/settings/service.py` per FR-006 / SC-004
- [X] T036 [US4] Implement `POST /settings/reset` in `backend/app/api/settings.py` and `resetSettings` in `frontend/src/services/settingsApi.ts` per `contracts/operator-defaults-api.md` / FR-007
- [X] T037 [US4] Add Reset control with confirmation in `frontend/src/features/settings/`; on success reload form from response; assert no session/run/comparison create side effects
- [X] T038 [US4] Surface Save validation errors clearly in Settings UI; ensure Save/Reset and error text remain usable at approximately 375px width without hover-only controls in `frontend/src/features/settings/` per FR-011 / SC-004 / SC-006
- [X] T039 [US4] Run T033–T034; fix until passing

**Checkpoint**: SC-004 / SC-005 — safe reject + Reset

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, regression, quickstart readiness

- [X] T040 [P] Update `docs/ROADMAP.md` Feature 008 status to reflect implementation progress when appropriate (IN PROGRESS / DONE only when criteria met)
- [X] T041 [P] Add brief Settings usage note to root `README.md` or Auto Trading docs only if the project already documents feature surfaces there (skip if no parallel pattern)
- [X] T042 Run full settings + related contract suite from `specs/008-trading-experiment-defaults/quickstart.md` automated section; fix failures
- [X] T043 [P] Manual quickstart smoke checklist in `specs/008-trading-experiment-defaults/quickstart.md` (steps 1–7) — mark Done-when items when observed
- [X] T044 Confirm primary nav still has exactly three areas in `frontend/src/config/primaryAreas.ts` / `frontend/src/__tests__/primaryNavigation.test.tsx`
- [X] T045 Propose commit message(s) for Feature 008; do not auto-commit unless asked

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies
- **Phase 2 (Foundational)** → after Setup; **blocks all user stories**
- **Phase 3 (US1)** → after Foundational — MVP Save UI
- **Phase 4 (US2)** → after US1 Save path (needs persisted Settings to seed forms meaningfully); can start helper stubs once GET exists
- **Phase 5 (US3)** → after US1 Save (needs PUT) and at least one create API; can run largely in parallel with US2 UI once Save works
- **Phase 6 (US4)** → after US1 PUT; Reset can parallel US2/US3 after foundational
- **Phase 7 (Polish)** → after desired stories complete

### User Story Dependencies

```text
Phase 2 Foundational
        │
        ▼
      US1 Save (MVP) ──────────────┐
        │                          │
        ├──────────► US2 Form seed │
        ├──────────► US3 History   │  (parallel after Save)
        └──────────► US4 Reset/validate
                                   │
                                   ▼
                                Polish
```

- **US1**: Delivers MVP (persist + Settings tab)
- **US2**: Depends on US1 Save + Foundational GET
- **US3**: Mostly verification; depends on Save + existing create APIs
- **US4**: Depends on Save validation path; Reset independent of form seeding

### Within Each User Story

1. Tests (write/extend first where listed)
2. Backend API/service behavior
3. Frontend wiring
4. Story verification run

### Parallel Opportunities

- Phase 1: T002 / T003 [P]
- Phase 2: T005, T009, T010, T011 [P] after model/service exist as noted
- US1: T013 / T014 [P]; T016 [P] with T015 once contract stable
- US2: T023 / T024 [P] after shared helper T021
- US3: T028 / T029 [P]
- US4: T033 / T034 [P]
- Polish: T040, T041, T043 [P]

---

## Parallel Example: User Story 1 (MVP)

```bash
# After Phase 2:
Task: "Contract PUT tests in backend/tests/contract/test_settings_api.py"
Task: "Frontend settings.test.tsx Save round-trip"

# Backend + client:
Task: "PUT /settings in backend/app/api/settings.py"
Task: "settingsApi.ts get/put client"

# Then UI:
Task: "Settings form + AutoTradingPage Settings tab"
Task: "Strategy change resets params in Settings draft"
```

---

## Parallel Example: User Story 2

```bash
# After shared mapper:
Task: "SessionConfigForm fresh init from Settings"
Task: "BacktestConfigForm fresh init from Settings"   # parallel
Task: "ComparisonConfigForm shared + leg0 only"       # parallel
Task: "settingsFormInit.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (model, starters, GET)
3. Complete Phase 3: US1 PUT + Settings tab Save
4. **STOP and VALIDATE**: Save → reload Settings shows same values
5. Demo MVP

### Incremental Delivery

1. Setup + Foundational → read Settings / starters
2. US1 → Save + Settings tab MVP
3. US2 → form prefill (fresh open; comparison leg0)
4. US3 → history immunity proofs
5. US4 → validation UX + Reset
6. Polish → quickstart green, roadmap, nav check

### Suggested MVP scope

**US1 only** (Settings persist + Auto Trading Settings tab). US2 is the user-visible payoff and should follow immediately in the same feature delivery when capacity allows.

---

## Notes

- [P] = different files, no incomplete dependencies
- [USn] maps to spec user stories 1–4
- Commit only when asked; keep Settings free of trading authority
- Do not store durationSeconds or historical windows in Settings (v1)
- Simulation capital starters shift to Settings/`1000` when seeded — intentional per research Decision 3

---

## Task Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 45 |
| **US1** | 7 (T013–T019) |
| **US2** | 8 (T020–T027) |
| **US3** | 5 (T028–T032) |
| **US4** | 7 (T033–T039) |
| **Setup + Foundational + Polish** | 18 (T001–T012, T040–T045) |
| **Parallel opportunities** | Yes — marked [P] across phases |

**Format validation**: All tasks use `- [ ]`, Task IDs T001–T045, [P]/[USn] where required, and file paths in descriptions.

---

## Phase 8: Convergence

**Purpose**: Close gaps found by `/speckit-converge` against spec/plan/tasks vs current code

- [X] T046 After successful Simulation / Backtest / Comparison create (and any discard that clears the draft), clear the create-form draft and re-seed from `GET /settings` in `frontend/src/features/simulation/SessionConfigForm.tsx`, `frontend/src/features/backtest/BacktestConfigForm.tsx`, and `frontend/src/features/comparison/ComparisonConfigForm.tsx` (or remount via `key` from `frontend/src/pages/AutoTradingPage.tsx`) per FR-004 (partial)
- [X] T047 [P] Add frontend test that switching preferred strategy in Settings resets params to registry defaults in `frontend/src/__tests__/settings.test.tsx` per FR-003 / T014 (missing)
- [X] T048 [P] Strengthen Comparison form-init test to assert leg 0 uses Settings preferred strategy/params and leg 1+ uses product/registry starters in `frontend/src/__tests__/settingsFormInit.test.tsx` per FR-004 / T020 (partial)
- [X] T049 [P] Fix orphan CSS declarations after `.settings-form` in `frontend/src/styles.css` (stray rules without a selector) per FR-011 / polish (unrequested)
- [X] T050 [P] Extend history-immunity coverage to Simulation and/or Comparison create → change Settings → historical artifact unchanged in `backend/tests/contract/test_settings_history_immunity.py` per FR-005 / SC-003 / US3 (partial)
