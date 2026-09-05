# Tasks: UGE Grammatical Evolution Search

**Input**: Design documents from `/specs/019-uge-grammatical-evolution/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context and SC-001–SC-005 / Independent
Test criteria require unit + integration gates. Spec FR-008 fail-closed
evaluation and train-only selection are test-backed.

**Organization**: Tasks grouped by user story for independent implementation
and testing.

**Spec precedence** (Session 2026-09-05 clarifications + plan/research):

- Call FORGE `uge` only; never copy/vendor FORGE/UGE source
- Default fitness `netProfit − buyAndHoldNetProfit` (maximise); `fitnessId`
  allow-list for alternate **single** scalars; no multi-objective (022)
- Discrete BNF parameter alternatives only (editable grammar); no continuous ranges
- Chronological train/val/test; **train-only** selection; val = post-run report;
  test holdout until freeze
- Evaluate via Feature 016 `evaluate_phenotype` on train candles during search
- Persist best phenotype; **Backtest UI selectable**; Strategy Comparison
  multi-run **not** required for DONE
- No Real / no auto Simulation from UGE
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/019-uge-grammatical-evolution/`, `docs/FORGE_INTEGRATION.md`
- FORGE (external): `/home/aghil/Documents/my document/limerick/projects/FORGE`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout + FORGE `uge` dependency verification

- [x] T001 Create package dir `backend/app/uge_search/` with `__init__.py` and `grammars/` per plan.md
- [x] T002 [P] Verify editable FORGE `uge` install in backend venv (`from uge import UGEEngine, Grammar, EvaluationResult, Fitness`) and confirm steps in `docs/FORGE_INTEGRATION.md`
- [x] T003 [P] Ensure `backend/tests/unit/` and `backend/tests/integration/` exist for uge_search tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Splits, errors, fitness ids, MVP grammar file — required before user stories

**WARNING**: No user story work until this phase completes

- [x] T004 Implement error types/codes for UGE search failures in `backend/app/uge_search/errors.py`
- [x] T005 [P] Implement chronological `chronological_split` (default 0.6/0.2/0.2, ordered by `openTime`) in `backend/app/uge_search/splits.py` per research.md R6
- [x] T006 [P] Implement fitness id allow-list (`net_minus_bh` default, `net_profit` minimum alternate) helpers in `backend/app/uge_search/fitness.py` per FR-005
- [x] T007 Create discrete-param MVP BNF `backend/app/uge_search/grammars/trading_mvp.bnf` covering ≥2 leaves now (`rsi`, `dual_ema` and/or `macd`) + ≥1 of `and`/`or`/`vote` (T017 completes all three leaves) per FR-002 / US2
- [x] T008 [P] Implement `load_trading_mvp_grammar` wrapping `Grammar.from_path` / `from_text` in `backend/app/uge_search/grammar_mvp.py`
- [x] T009 [P] Unit tests for splits + fitness id allow-list + grammar load in `backend/tests/unit/test_uge_search_splits_grammar.py`

**Checkpoint**: Foundation ready — no UGE loop yet

---

## Phase 3: User Story 1 - Offline UGE run (Priority: P1) — MVP core

**Goal**: Operator/researcher can run offline UGE on a fixed candle snapshot + grammar and get a best phenotype + train fitness, reproducible by seed; validation reported post-run; test unused for selection.

**Independent Test**: Same seed + data + grammar + config → same best phenotype; train fitness matches standalone `evaluate_phenotype` on train candles for that phenotype; selection never reads test candles.

### Tests for User Story 1

- [x] T010 [P] [US1] Unit tests for Backtest evaluator → `EvaluationResult` success/fail-closed in `backend/tests/unit/test_uge_search_fitness.py`
- [x] T011 [P] [US1] Integration tests: tiny pop/ngen seeded `run_uge_search` completes, seed replay, train fitness matches 016 evaluate in `backend/tests/integration/test_uge_offline_run.py`

### Implementation for User Story 1

- [x] T012 [US1] Implement `make_backtest_evaluator(train_candles, fitness_id, capital/fees…)` calling Feature 016 `evaluate_phenotype` in `backend/app/uge_search/fitness.py`
- [x] T013 [US1] Implement `run_uge_search` using FORGE `UGEEngine` or `run(EngineRunConfig)` with train-only evaluator context in `backend/app/uge_search/runner.py`
- [x] T014 [US1] After run, compute validation fitness for best phenotype only (report; do not re-rank) in `backend/app/uge_search/runner.py`
- [x] T015 [US1] Export public API `chronological_split`, `load_trading_mvp_grammar`, `make_backtest_evaluator`, `run_uge_search` from `backend/app/uge_search/__init__.py`

**Checkpoint**: US1 — offline seeded UGE works without UI

---

## Phase 4: User Story 2 - Search parameters and combinations (Priority: P1)

**Goal**: Grammar includes ≥2 strategies, discrete parameter choices, and ≥1 composition op; invalid phenotypes fail closed without crashing the run.

**Independent Test**: Sampled/generated phenotypes vary; unknown/invalid forms yield `EvaluationResult(ok=False)` and the run continues; composition phenotypes appear among valid mappings.

### Tests for User Story 2

- [x] T016 [P] [US2] Unit/integration assertions that grammar produces leaf+compose variety and invalid eval does not abort run in `backend/tests/unit/test_uge_search_grammar_variety.py` (and/or extend `test_uge_offline_run.py`)

### Implementation for User Story 2

- [x] T017 [US2] Expand/verify `backend/app/uge_search/grammars/trading_mvp.bnf` discrete alternatives for all three MVP leaves (`rsi`, `macd`, `dual_ema`) and `and`/`or`/`vote` compose-of-leaves forms
- [x] T018 [US2] Document operator-editable discrete alternatives and max_depth knobs in `specs/019-uge-grammatical-evolution/quickstart.md` (and brief comment header in the `.bnf` file)

**Checkpoint**: US2 — searchable combination space present

---

## Phase 5: User Story 3 - Frozen phenotype + Backtest UI (Priority: P2)

**Goal**: Persist best phenotype; select it in Backtest UI; re-run without live UGE. No Strategy Comparison multi-run; no auto Simulation/Real.

**Independent Test**: JSON artifact loads; Backtest UI can select frozen phenotype / `torque_phenotype`; completed Backtest metrics match 016 evaluate of that string; no UGE process required.

### Tests for User Story 3

- [x] T019 [P] [US3] Unit tests for persist/load frozen artifact in `backend/tests/unit/test_uge_search_persist.py`
- [x] T020 [P] [US3] Backend tests that Backtest accepts `torque_phenotype` (or frozen id) and runs via 016 bind in `backend/tests/integration/test_uge_frozen_backtest.py`
- [x] T021 [P] [US3] Frontend test that Backtest strategy/phenotype selector can choose a frozen phenotype option in `frontend/src/__tests__/backtestPhenotypeSelect.test.tsx` (or equivalent)

### Implementation for User Story 3

- [x] T022 [US3] Implement `persist_run_result` / `load_frozen_phenotype` JSON under `backend/data/uge_runs/` (configurable path) in `backend/app/uge_search/persist.py`
- [x] T023 [US3] Register Backtest-selectable `torque_phenotype` strategy (param: phenotype string) wrapping 016 bind in `backend/app/uge_search/phenotype_strategy.py` and ensure import/registration from `backend/app/strategy/__init__.py` or `backend/app/main.py`
- [x] T024 [US3] API to list frozen artifacts and/or return last run result for UI in `backend/app/api/uge.py` mounted from `backend/app/main.py`
- [x] T025 [US3] Wire Backtest UI to select a frozen phenotype artifact or enter/select `torque_phenotype` in `frontend/src/features/backtest/` (and proxy `/uge` in `frontend/vite.config.ts` if needed)
- [x] T026 [US3] Export persist helpers from `backend/app/uge_search/__init__.py`

**Checkpoint**: US3 — freeze → Backtest UI path complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Safety, docs, gates, roadmap

- [x] T027 [P] Confirm no FORGE/UGE source vendored under repo; Strategy/Controller/Risk do not import `uge` (extend import-guard tests in `backend/tests/unit/test_uge_search_fitness.py` or dedicated guard file)
- [x] T028 [P] Update `specs/019-uge-grammatical-evolution/quickstart.md` with exact pytest module names and Backtest UI smoke steps
- [x] T029 Run quickstart automated gates (`pytest` for uge_search unit + integration) from `backend/`
- [x] T030 [P] Update Feature 019 status in `docs/ROADMAP.md` only after implement complete and T029 green (do not mark DONE in this tasks-only step)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Can largely parallel US1 after T007/T008; strengthen grammar after or with US1
- **US3 (Phase 5)**: Depends on US1 `run_uge_search` (or manual phenotype) for persist; Backtest UI can use hand-written phenotype for partial test
- **Polish (Phase 6)**: Depends on US1–US3 complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — core MVP
- **US2 (P1)**: Grammar richness; shares T007 foundation
- **US3 (P2)**: Needs persist + Backtest path; ideally after US1 produces a best phenotype

### Parallel Opportunities

- T002 ‖ T003 after T001
- T005 ‖ T006 ‖ T008 after T004/T007 as noted
- T010 ‖ T011 early with implementation
- T019 ‖ T020 ‖ T021 in US3
- T027 ‖ T028 in polish

---

## Parallel Example: User Story 1

```bash
# After Foundational:
Task: "Unit tests for evaluator in backend/tests/unit/test_uge_search_fitness.py"
Task: "Implement make_backtest_evaluator in backend/app/uge_search/fitness.py"
# Then: runner → validation report → exports → integration tests green
```

---

## Implementation Strategy

### MVP First (US1)

1. Setup + Foundational (splits, grammar, fitness ids)
2. US1 `run_uge_search` on fixture candles
3. STOP and VALIDATE: seed replay + train fitness match
4. US2 grammar completeness
5. US3 persist + Backtest UI selection

### Incremental Delivery

1. Foundation → grammar + splits ready
2. US1 → offline search proof
3. US2 → combination/param discrete space
4. US3 → operator Backtest reuse in UI
5. Polish → quickstart green

### Suggested MVP scope

**US1 + US2** for search proof; ship **US3** in the same implement pass when possible (operator asked for Backtest UI freeze). Skip Strategy Comparison multi-run.

### 019 DONE criteria

- Required: T001–T026 path green (or equivalent covering SC-001–SC-005)
- Required: T027–T029 safety/quickstart gates
- Not required: Strategy Comparison multi-run; Real; continuous live UGE
- T030 ROADMAP DONE only after gates green

---

## Notes

- [P] = different files, no incomplete dependencies
- Do not implement Feature 015 Real or 024 autonomous from phenotypes
- Do not vendor FORGE
- Commit only when the operator asks
