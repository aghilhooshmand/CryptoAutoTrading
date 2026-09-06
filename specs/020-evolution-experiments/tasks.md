# Tasks: Evolution Experiments & Results (UGE Lab)

**Input**: Design documents from `/specs/020-evolution-experiments/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context, Independent Test criteria, SC-001–
SC-005, and quickstart.md require unit + integration (+ frontend) gates.

**Organization**: Tasks grouped by user story. Delivery labels in descriptions:
**[020a]** = US1+US2, **[020b]** = US3, **[020c]** = US4.

**Execution order:** Always **020a → 020b → 020c** (US1→US2→US3→US4). US4’s P1
priority tag does **not** mean implement freeze before structured grammar.

**Spec precedence** (Session 2026-09-06 clarifications + plan/research):

- Call FORGE `uge` only; never copy/vendor FORGE source
- One concurrent experiment; in-process background thread; HTTP poll (no WebSocket)
- Stream **per completed generation** via FORGE `reporters=`
- **020a**: run/stream/charts/persist — **no** named strategy freeze
- **020b**: structured leaf/op/param UI only — **no** raw BNF editor
- **020c**: terminal-only freeze → separate named strategy; reject duplicate
  displayName; selectable in Backtest/Sim/Real; lab never auto-places Real
- Train-only selection unchanged (019); propose commits only (no auto-commit)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/020-evolution-experiments/`, `docs/ROADMAP.md`
- FORGE (external): `/home/aghil/Documents/my document/limerick/projects/FORGE`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Experiment package layout + data dirs + nav placeholder

- [x] T001 Create dirs `backend/app/uge_search/` extensions targets
      (`experiment_store.py`, `experiment_runner.py` stubs ok) and
      `backend/data/uge_experiments/` (gitkeep) per plan.md
- [x] T002 [P] Create frontend feature dir `frontend/src/features/evolution/`
      with placeholder `EvolutionPage.tsx` and `evolutionApi.ts`
- [x] T003 [P] Ensure Vite proxies `/uge` (extend `frontend/vite.config.ts` if
      missing) for experiment routes alongside existing frozen routes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persist model + singleton job shell + runner hooks — blocks US1–US4

**WARNING**: No user story work until this phase completes

- [x] T004 Implement experiment + generation persistence
      (`meta.json` + `generations.jsonl`) in
      `backend/app/uge_search/experiment_store.py` per data-model.md
- [x] T005 [P] Extend `run_uge_search` (or add `run_uge_search_with_hooks`) in
      `backend/app/uge_search/runner.py` to accept `on_generation` callback and
      `cancel_check` using FORGE `reporters=` (research.md R1)
- [x] T006 Implement singleton `ExperimentRunner` (start/cancel/status; one
      active run; background thread) in
      `backend/app/uge_search/experiment_runner.py` per research.md R2
- [x] T007 [P] Unit tests for store append + singleton 409 behavior in
      `backend/tests/unit/test_uge_experiment_store_runner.py`
- [x] T008 Export new experiment helpers from
      `backend/app/uge_search/__init__.py` without breaking 019 exports

**Checkpoint**: Foundation ready — can start US1 API/UI

---

## Phase 3: User Story 1 - Configure and start UGE experiment (Priority: P1) — 020a MVP

**Goal**: Operator configures UGE params + candle window in Evolution UI, starts
offline search without Python shell; invalid config rejected; cancel works.

**Independent Test**: From UI/API alone, start short seeded run; reaches
terminal state with best phenotype or clear failure; second concurrent start →
409; cancel → `cancelled`.

### Tests for User Story 1

- [x] T009 [P] [US1] Contract/API tests for `POST/GET/cancel`
      `/uge/experiments` in `backend/tests/contract/test_uge_experiments_api.py`
      per `contracts/evolution-experiments-api.md`
- [x] T010 [P] [US1] Integration: create experiment loads candles, rejects short
      window / bad splits in `backend/tests/integration/test_uge_experiment_create.py`

### Implementation for User Story 1

- [x] T011 [US1] [020a] Implement HTTP routes create/list/get/cancel in
      `backend/app/api/uge.py` (or `backend/app/api/evolution.py` mounted from
      `backend/app/main.py`) per evolution-experiments-api.md
- [x] T012 [US1] [020a] Wire create → validate config → load candles (existing
      market-data/backtest fetch) → `ExperimentRunner.start` in experiment
      service module under `backend/app/uge_search/` (e.g. `experiment_service.py`)
- [x] T013 [US1] [020a] Implement `ExperimentConfigForm` + start/cancel controls
      (fields: populationSize, nGenerations, seed, fitnessId, train/val/test
      ratios, symbol/timeframe/start/end, capital/fee/slippage) in
      `frontend/src/features/evolution/ExperimentConfigForm.tsx` and API
      client methods in `frontend/src/features/evolution/evolutionApi.ts`
- [x] T014 [US1] [020a] Add Evolution route + primary/secondary nav link in
      `frontend/src/` (app router / nav components used by other features)
- [x] T015 [P] [US1] Frontend test for config validation + start button wiring
      in `frontend/src/__tests__/evolutionConfig.test.tsx`

**Checkpoint**: US1 — experiment can be started/cancelled from UI (progress UI
may be minimal until US2)

---

## Phase 4: User Story 2 - Watch evolution stream and charts (Priority: P1) — 020a

**Goal**: While running, each completed generation appears via poll; fitness
chart updates; terminal view shows best phenotype + train/val metrics. No named
strategy freeze.

**Independent Test**: Multi-generation run shows gen k in API/UI before run
ends; completed view has chart series + best phenotype text.

### Tests for User Story 2

- [x] T016 [P] [US2] Integration: generations append before terminal status;
      assert evaluator uses train-split candles only (FR-017) in
      `backend/tests/integration/test_uge_experiment_stream.py` (quickstart 020a)
- [x] T017 [P] [US2] Frontend test: progress/chart renders generation points in
      `frontend/src/__tests__/evolutionProgress.test.tsx`

### Implementation for User Story 2

- [x] T018 [US2] [020a] Ensure `GET /uge/experiments/{id}` and
      `GET /uge/experiments/{id}/generations` return growing snapshots while
      `running` in `backend/app/api/uge.py` + store
- [x] T019 [US2] [020a] Persist best-so-far / terminal best + validation report
      fields on experiment meta in `backend/app/uge_search/experiment_runner.py`
      / store (no catalogue registration)
- [x] T020 [US2] [020a] Implement `ExperimentProgress.tsx` (poll ~1s, generation
      table, fitnessMax/Avg chart) in
      `frontend/src/features/evolution/ExperimentProgress.tsx`
- [x] T021 [US2] [020a] Compose Evolution page (config + progress + best
      phenotype panel) in `frontend/src/features/evolution/EvolutionPage.tsx`

**Checkpoint**: US2 — 020a lab runnable with live gens + charts (MVP lab demo)

---

## Phase 5: User Story 3 - Structured grammar & operators (Priority: P2) — 020b

**Goal**: Operator selects leaves, composition ops, discrete param alternatives;
system builds grammar; empty/invalid space rejected; phenotypes honor allow-list.

**Independent Test**: Restrict to `dual_ema`+`rsi` and `and` only → no `macd` /
`or`/`vote` in produced best samples; empty leaves → start rejected.

### Tests for User Story 3

- [x] T022 [P] [US3] Unit tests for grammar builder constraints in
      `backend/tests/unit/test_uge_grammar_builder.py`
- [x] T023 [P] [US3] Integration/API test: structured body restricts search space
      in `backend/tests/integration/test_uge_experiment_structured_grammar.py`

### Implementation for User Story 3

- [x] T024 [US3] [020b] Implement `grammar_builder.build_grammar(...)` →
      `Grammar` / BNF text in `backend/app/uge_search/grammar_builder.py` per
      research.md R6 (ParamDef-aligned discrete alts)
- [x] T025 [US3] [020b] Plumb `leaves` / `compositionOps` / `paramAlternatives`
      from create body through runner in `backend/app/uge_search/experiment_service.py`
      and `runner.py`
- [x] T026 [US3] [020b] Add structured controls to
      `frontend/src/features/evolution/ExperimentConfigForm.tsx` (no raw BNF
      textarea)
- [x] T027 [P] [US3] Frontend test for leaf/op selection + reject empty leaves
      in `frontend/src/__tests__/evolutionStructuredConfig.test.tsx`

**Checkpoint**: US2+US3 — searchable space controllable from UI

---

## Phase 6: User Story 4 - Freeze into named strategy catalogue (Priority: P1) — 020c

**Goal**: Terminal experiment with best phenotype freezes to unique named
strategy; appears in `GET /strategies`; usable in Backtest + Simulation (+ Real
picker when available). Reject duplicate names; no mid-run freeze; lab does not
place Real orders.

**Independent Test**: Freeze → catalogue id → Backtest + Simulation create/run;
duplicate name 400; freeze while running rejected.

### Tests for User Story 4

- [x] T028 [P] [US4] Unit tests: unique displayName, Torque-check fail closed,
      terminal-only in `backend/tests/unit/test_uge_frozen_catalogue.py`
- [x] T029 [P] [US4] Integration: freeze → strategies list → backtest path in
      `backend/tests/integration/test_frozen_catalogue_backtest.py`
- [x] T030 [P] [US4] Frontend test for freeze form + duplicate error in
      `frontend/src/__tests__/evolutionFreeze.test.tsx`

### Implementation for User Story 4

- [x] T031 [US4] [020c] Implement durable catalogue + registry register/load in
      `backend/app/uge_search/frozen_catalogue.py` under
      `backend/data/uge_frozen_strategies/` per
      `contracts/frozen-strategy-catalogue.md`
- [x] T032 [US4] [020c] `POST /uge/experiments/{id}/freeze` in
      `backend/app/api/uge.py`; load catalogue on startup in
      `backend/app/main.py`
- [x] T033 [US4] [020c] Ensure frozen ids appear in `GET /strategies` via
      registry (`backend/app/strategy/registry.py` integration /
      `frozen_catalogue.py`)
- [x] T034 [US4] [020c] `FreezeStrategyForm.tsx` on Evolution page; call freeze
      API; show new strategy id in
      `frontend/src/features/evolution/FreezeStrategyForm.tsx`
- [x] T035 [US4] [020c] Verify Backtest, Simulation, and Real session forms that
      use `StrategyConfigFields` / `frontend/src/features/strategy/` list frozen
      catalogue entries; fix gaps if missing (Real gated OK if create UI absent)
- [x] T036 [US4] [020c] Confirm Evolution UI has no Real auto-start; document
      Real selection uses same strategyId when 015 exists in
      `specs/020-evolution-experiments/quickstart.md`

**Checkpoint**: US4 — freeze → trade-mode selection path complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Safety, docs, gates, roadmap

- [x] T037 [P] Import guards: experiment runner must not import Real place;
      Strategy/Controller/Risk must not import `uge` — extend
      `backend/tests/unit/test_uge_search_fitness.py` or
      `backend/tests/unit/test_uge_experiment_guards.py`
- [x] T038 [P] Update `specs/020-evolution-experiments/quickstart.md` with exact
      pytest module names and UI smoke steps matching implemented paths
- [x] T039 Run quickstart automated gates for 020a then 020b/020c from
      `backend/` (+ frontend vitest for evolution tests)
- [x] T040 [P] Update Feature 020 status / phase notes in `docs/ROADMAP.md`
      only after T039 green and operator accepts phase DONE (do not mark full
      020 DONE until US1–US4 complete)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all stories
- **US1 (Phase 3)**: Depends on Foundational — **020a MVP start**
- **US2 (Phase 4)**: Depends on US1 create/runner — **020a stream/charts**
- **US3 (Phase 5)**: Depends on Foundational + US1 create path — **020b**
  (can start after US1 API exists; ideally after US2 for full lab UX)
- **US4 (Phase 6)**: Depends on US1 terminal experiments (US2 improves UX) —
  **020c**
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — MVP
- **US2 (P1)**: Needs US1 running experiments
- **US3 (P2)**: Needs create API; independent of charts
- **US4 (P1)**: Needs terminal experiment with best phenotype (US1 sufficient;
  US2 recommended)

### Parallel Opportunities

- T002 ‖ T003 after T001
- T005 ‖ T007 after T004/T006 as noted
- T009 ‖ T010 in US1
- T016 ‖ T017 in US2
- T022 ‖ T023 in US3
- T028 ‖ T029 ‖ T030 in US4
- T037 ‖ T038 in polish

---

## Parallel Example: User Story 1

```bash
# After Foundational:
Task: "Contract tests in backend/tests/contract/test_uge_experiments_api.py"
Task: "Integration create tests in backend/tests/integration/test_uge_experiment_create.py"
# Then: API routes → service → ExperimentConfigForm → nav → frontend test
```

## Parallel Example: User Story 2

```bash
Task: "Integration stream test in backend/tests/integration/test_uge_experiment_stream.py"
Task: "Frontend progress test in frontend/src/__tests__/evolutionProgress.test.tsx"
# Then: generations GET → persist best → ExperimentProgress → EvolutionPage
```

---

## Implementation Strategy

### MVP First (020a = US1 + US2)

1. Phase 1 Setup + Phase 2 Foundational
2. Phase 3 US1 (start/cancel)
3. Phase 4 US2 (stream/charts)
4. **STOP and VALIDATE** quickstart 020a — lab demo without freeze/grammar UI

### Incremental Delivery

1. 020a (US1+US2) → demo Evolution lab
2. 020b (US3) → structured search space
3. 020c (US4) → named strategy freeze → Backtest/Sim
4. Polish → ROADMAP status

### Suggested MVP scope

**US1 + US2 (020a)** only — matches clarification that named freeze is 020c.

---

## Notes

- [P] = different files, no incomplete dependencies
- Do not implement raw BNF editor or WebSockets
- Do not register named strategies in 020a tasks (US1/US2)
- Keep 019 `run_uge_search` / `/uge/frozen` working
- Commit only when operator asks

---

## Phase 8: Convergence

**Purpose**: Close gaps found by `/speckit-converge` against spec/plan vs current code (2026-09-06).

- [x] T041 [US3] Add discrete parameter-alternative editors to `frontend/src/features/evolution/ExperimentConfigForm.tsx` and send `paramAlternatives` via `evolutionApi.ts` / create body per FR-009 (partial)
- [x] T042 [US2] Add experiment list + select to resume polling in `frontend/src/features/evolution/EvolutionPage.tsx` (and `listExperiments` in `evolutionApi.ts`) so reconnect mid-run works per Edge Cases (missing)
- [x] T043 [P] [US1] Add create-path reject tests (short candle window, invalid splits) in `backend/tests/integration/test_uge_experiment_create.py` per US1/AC2 / T010 (missing)
- [x] T044 [P] [US3] Add structured leaves/ops phenotype constraint integration test in `backend/tests/integration/test_uge_experiment_structured_grammar.py` per US3 / SC-004 / T023 (missing)
