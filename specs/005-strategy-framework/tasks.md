# Tasks: Strategy Framework and Selection

**Input**: Design documents from `/specs/005-strategy-framework/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md
    
**Tests**: Included — plan Technical Context and constitution XXVIII require registry/validation/continuity, contract, and UI tests. Spec SC-002–SC-007 are test-backed.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Spec precedence** (Session 2026-08-11 clarifications + plan tightenings):
- Dual EMA is the strategy; **9/21 is default configuration** (editable periods)
- Canonical id `dual_ema`; alias `dual_ema_9_21` → Dual EMA; new creates persist `dual_ema`
- Omit `strategyId` → reject (UI may pre-fill)
- Warm-up until `S+1`; backtest `insufficient_history` if count `< S`
- Legacy/unknown id: **READ** ok; **START/RESUME** forbidden for unknown; **NEW create** forbidden for unknown (FR-010)
- Cross-field validation: strategy-level message “Fast period must be less than slow period.” (no rule engine)
- Same Dual EMA implementation for Simulation and Backtest
- Local UI: Vite MUST proxy `/strategies` (T040)
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/005-strategy-framework/`, root `README.md` only if needed

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package/layout markers — no trading behavior yet

- [X] T001 Create backend package dir `backend/app/strategy/` and frontend dir `frontend/src/features/strategy/` per plan.md
- [X] T002 [P] Add package marker `backend/app/strategy/__init__.py`
- [X] T003 [P] Ensure `backend/tests/unit/`, `backend/tests/contract/`, `backend/tests/integration/` exist for new strategy tests
- [X] T040 [P] Proxy `/strategies` to the backend in `frontend/vite.config.ts` (same pattern as `/simulation` and `/backtest`) so local UI can call `GET /strategies`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared strategy contract, registry, Dual EMA migration, DB columns, resolve/validate helpers — required before any user story

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T004 Move/adapt strategy protocol (`CandleClose`, `SignalSide`, `StrategySignal`, `Strategy`) into `backend/app/strategy/base.py` from `backend/app/simulation/strategy/base.py`
- [X] T005 [P] Implement ParamDef + validate helpers (defaults merge, min/max, strategy-level constraints message) in `backend/app/strategy/params.py`
- [X] T006 Implement registry (register, list, resolve alias→canonical, `validate_and_materialize`, unknown reject) in `backend/app/strategy/registry.py`
- [X] T007 Migrate Dual EMA into `backend/app/strategy/dual_ema.py` with configurable `fast`/`slow` (defaults 9/21), warm-up HOLD while count `< S+1`, `min_history_candles() -> S`, and register as `dual_ema` with alias `dual_ema_9_21`
- [X] T008 Add thin re-exports or update imports so existing `backend/app/simulation/strategy/` consumers do not break during migration
- [X] T009 Add `strategy_params` JSON text column (and ensure `strategy_id` semantics) on simulation session + backtest run models in `backend/app/db/models.py` per data-model.md
- [X] T010 [P] Unit tests for registry resolve/alias/defaults/omit/unknown and Dual EMA param validation (incl. message “Fast period must be less than slow period.”) in `backend/tests/unit/test_strategy_registry.py`
- [X] T011 [P] Unit tests for Dual EMA continuity (defaults 9/21 match pre-migration signals) and non-default periods in `backend/tests/unit/test_dual_ema_continuity.py` and `backend/tests/unit/test_dual_ema_params.py`
- [X] T012 Wire Dual EMA auto-registration on app import/startup (registry populated before routes serve) from `backend/app/strategy/` / `backend/app/main.py` as needed

**Checkpoint**: Shared registry + Dual EMA + DB columns ready; no story UI/API complete yet

---

## Phase 3: User Story 1 - Choose registered strategy for simulation (Priority: P1) 🎯 MVP core

**Goal**: Operator selects Dual EMA (defaults 9/21, editable periods) when creating a simulation session; params persisted; pipeline uses resolved strategy; omit/unknown/invalid fail safely; unknown stored id cannot START/RESUME.

**Independent Test**: Create session with `strategyId: dual_ema` (and with alias); confirm persisted canonical id + params; omit id → 400; invalid periods → 400 with fast&lt;slow message; session runs Dual EMA through Controller→Risk.

### Tests for User Story 1

- [X] T013 [P] [US1] Contract tests: `GET /strategies` schema; `POST /simulation/sessions` requires `strategyId`; alias→persist `dual_ema`; invalid params message in `backend/tests/contract/test_strategies_api.py` and extend `backend/tests/contract/test_simulation_api.py`
- [X] T014 [P] [US1] Frontend tests for strategy selector + period defaults/cross-field message in `frontend/src/__tests__/strategyConfig.test.tsx`

### Implementation for User Story 1

- [X] T015 [US1] Implement `GET /strategies` in `backend/app/api/strategies.py` and mount in `backend/app/main.py` per `contracts/strategy-api.md`
- [X] T016 [US1] Require `strategyId` + optional `strategyParams` on create; resolve/validate/persist canonical id + effective params in `backend/app/simulation/session_service.py` and `backend/app/api/simulation.py`
- [X] T017 [US1] Construct strategy from session effective params in `backend/app/simulation/pipeline.py` (no hard-coded Dual EMA-only import path that bypasses registry)
- [X] T018 [US1] Enforce START/RESUME fail-safe for unknown stored `strategy_id` in `backend/app/simulation/session_service.py` / pipeline (READ still allowed)
- [X] T019 [P] [US1] Add typed client `frontend/src/services/strategiesApi.ts` for `GET /strategies`
- [X] T020 [P] [US1] Implement `StrategyConfigFields.tsx` (selector, dynamic params, min/max, strategy-level constraint message) in `frontend/src/features/strategy/StrategyConfigFields.tsx`
- [X] T021 [US1] Wire strategy fields into `frontend/src/features/simulation/SessionConfigForm.tsx` (pre-fill `dual_ema`, send `strategyId` + `strategyParams`)
- [X] T022 [US1] Show strategy id + params on session status/detail in `frontend/src/features/simulation/SessionStatusPanel.tsx` (or related panel)
- [X] T023 [US1] Run T013–T014 and fix until passing

**Checkpoint**: Simulation create/select Dual EMA works end-to-end with fail-safe rules

---

## Phase 4: User Story 2 - Same strategy for backtest (Priority: P1)

**Goal**: Backtest create selects the same registered Dual EMA; insufficient history uses `S`; continuity for defaults; shared implementation (no fork).

**Independent Test**: Backtest with defaults persists `dual_ema` + `{9,21}`; custom slow=50 rejects short windows; continuity fixture matches pre-migration Dual EMA; engine resolves via registry.

### Tests for User Story 2

- [X] T024 [P] [US2] Contract/extend tests for backtest create strategy fields, alias, omit reject, insufficient `< S` in `backend/tests/contract/test_backtest_api.py`
- [X] T025 [P] [US2] Integration test: same Dual EMA registry path for sim + backtest on fixture in `backend/tests/integration/test_strategy_shared_sim_backtest.py`

### Implementation for User Story 2

- [X] T026 [US2] Require `strategyId` + optional `strategyParams` on backtest create; resolve/validate/persist in `backend/app/backtest/service.py` and `backend/app/api/backtest.py`
- [X] T027 [US2] Resolve strategy via registry in `backend/app/backtest/engine.py` using run’s effective params (remove hard Dual EMA-only construction that bypasses registry)
- [X] T028 [US2] Drive `insufficient_history` from Dual EMA `min_history_candles` / slow period `S` in `backend/app/backtest/limits.py` and `backend/app/backtest/service.py` (default S=21 preserves prior gate)
- [X] T029 [US2] Wire `StrategyConfigFields` into `frontend/src/features/backtest/BacktestConfigForm.tsx` (pre-fill `dual_ema`, send params)
- [X] T030 [US2] Run T024–T025 and T011 continuity checks; fix until passing

**Checkpoint**: Simulation and Backtest share Dual EMA via registry; history gate scales with `S`

---

## Phase 5: User Story 3 - Inspect which strategy ran (Priority: P2)

**Goal**: Completed/failed backtests and sessions expose strategy id + effective params after create and across restart (within retention).

**Independent Test**: GET session/run returns canonical id + params; UI results/list show them; legacy alias rows normalize on read without becoming executable if unknown.

### Tests for User Story 3

- [X] T031 [P] [US3] Contract assertions that GET simulation session and GET backtest run return `strategyId` + `strategyParams` (and alias normalize on read) in existing contract test files under `backend/tests/contract/`

### Implementation for User Story 3

- [X] T032 [US3] Normalize legacy `dual_ema_9_21` on serialize/read; keep unknown ids as-stored for GET only in `backend/app/simulation/session_service.py` and `backend/app/backtest/service.py` (or shared serializer helper)
- [X] T033 [US3] Show strategy id + params on backtest results/list surfaces in `frontend/src/features/backtest/BacktestResultsPanel.tsx` and/or `BacktestRunList.tsx`
- [X] T034 [US3] Run T031 and quickstart inspect scenarios; fix until passing

**Checkpoint**: Operators can see what strategy/params ran without re-opening the create form

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, guards, quickstart validation

- [X] T035 [P] Update root `README.md` briefly that Auto Trading strategies are selectable (Dual EMA defaults 9/21) and link `specs/005-strategy-framework/quickstart.md` if appropriate
- [X] T036 [P] Grep/guard: no second Dual EMA implementation under `backend/app/backtest/`; simulation/backtest import shared `app.strategy`
- [X] T037 Confirm START/RESUME refuses unknown stored strategy ids (add/adjust unit or contract coverage under `backend/tests/`)
- [X] T038 Run full validation scenarios in `specs/005-strategy-framework/quickstart.md`; fix gaps in `backend/app/strategy/` / UI
- [X] T039 Propose git commit message for Feature 005 implementation in chat (do not auto-commit unless asked)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — simulation selection MVP core
- **US2 (Phase 4)**: Depends on Foundational; preferably after US1 registry/API patterns exist — **required for shared Dual EMA path**
- **US3 (Phase 5)**: Depends on US1/US2 persistence fields existing
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1**: Foundational only
- **US2**: Foundational; reuses registry + `StrategyConfigFields` from US1 when sequenced
- **US3**: Needs create paths that persist strategy fields (US1 and/or US2)

### Within Each Story

- Tests first where listed; fail before implementation
- Registry/DB before API; API before UI wiring
- Story checkpoint before next priority when solo

### Parallel Opportunities

- Phase 1: T002 ∥ T003 ∥ T040
- Phase 2: T005 ∥ T010 ∥ T011 after base exists; T004→T006→T007 sequential on shared package
- US1: T013 ∥ T014; T019 ∥ T020 after `GET /strategies` (T040 before local UI smoke)
- US2: T024 ∥ T025
- Polish: T035 ∥ T036

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract tests GET /strategies + simulation create strategy fields"
Task: "Frontend strategyConfig.test.tsx"

# After API list exists:
Task: "strategiesApi.ts"
Task: "StrategyConfigFields.tsx"
```

---

## Parallel Example: User Story 2

```bash
Task: "Extend test_backtest_api.py for strategyId/params and insufficient < S"
Task: "Integration test_strategy_shared_sim_backtest.py"
```

---

## Implementation Strategy

### MVP First (US1 — simulation selection)

1. Phase 1 Setup  
2. Phase 2 Foundational (registry + Dual EMA + DB)  
3. Phase 3 US1 (simulation API + UI)  
4. **STOP and VALIDATE**: create with Dual EMA defaults/alias; omit/invalid fail  

### Demo-ready shared path (US1 + US2)

Treat **runnable Dual EMA selection across sim + backtest** as Phases 1–4 through US2 checkpoint (T030), matching FR-008.

### Incremental Delivery

1. Setup + Foundational → registry ready  
2. US1 → simulation selectable Dual EMA  
3. US2 → backtest same registry + `S` history gate  
4. US3 → inspect surfaces  
5. Polish → docs + quickstart  

---

## Notes

- [P] = different files, no incomplete sibling deps
- Runnable shared strategy path = **US1 + US2** (not US1 alone for FR-008)
- Exact messages: “Fast period must be less than slow period.”
- Lifecycle: READ ok / START-RESUME forbidden for unknown / NEW create forbidden for unknown
- Propose commits only; do not auto-commit unless asked
- Avoid: second Dual EMA fork, rule engine, mid-run strategy swap, fourth nav, real money

---

## Phase 7: Convergence

**Purpose**: Close remaining test gaps vs Success Criteria after Feature 005 implement (code paths already present).

- [ ] T041 Strengthen Dual EMA continuity tests with a fixed closed-candle fixture and locked BUY/SELL/HOLD sequence for default 9/21 in `backend/tests/unit/test_dual_ema_continuity.py` per SC-003 / FR-009 (partial)
- [ ] T042 Add an assertion that strategy evaluation does not mutate cash/positions (Controller→Risk→Execution remains the only balance path) under `backend/tests/` per SC-004 / FR-002 (partial)
