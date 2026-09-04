# Tasks: Torque Trading Program Core

**Input**: Design documents from `/specs/016-torque-trading-program/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context and SC-001–SC-004 / Independent
Test criteria require unit + Backtest fixture gates. Spec FR-008 fail-closed
and quickstart automated gates are test-backed.

**Organization**: Tasks grouped by user story for independent implementation
and testing.

**Spec precedence** (Session 2026-09-04 + plan/research):

- Call FORGE `torque.check` only; never copy/vendor FORGE source
- Leaves = existing registry strategies (`rsi`, `macd`, `dual_ema` minimum)
- Keywords = ParamDef names (`period`, `fastPeriod`, …); positional leaf args out of MVP
- Composition: `and` / `or` / `vote` agreement-style on BUY/SELL/HOLD (research R5)
- Evaluate via Feature 004 Backtest `run_engine` (deterministic); Simulation optional
- No RealExecutionAdapter / Kraken place; Feature 015 paused
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Docs: `specs/016-torque-trading-program/`, `docs/FORGE_INTEGRATION.md`
- FORGE (external): `/home/aghil/Documents/my document/limerick/projects/FORGE`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout + FORGE dependency verification — no trading behavior yet

- [x] T001 Create package dir `backend/app/torque_bind/` with `__init__.py` per plan.md
- [x] T002 [P] Verify editable FORGE install in backend venv (`from torque import check`) and document command in `docs/FORGE_INTEGRATION.md` if missing steps
- [x] T003 [P] Ensure `backend/tests/unit/` and `backend/tests/integration/` exist for new torque_bind tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error codes, catalogue of leaf/composition names — required before any user story

**WARNING**: No user story work until this phase completes

- [x] T004 Implement stable error types/codes (`invalid_torque_form`, `unknown_torque_leaf`, `invalid_torque_params`, `invalid_composition`, `evaluate_failed`) in `backend/app/torque_bind/errors.py` per contracts/torque-bind-api.md
- [x] T005 [P] Implement leaf + composition catalogue in `backend/app/torque_bind/catalogue.py`: MVP leaves `rsi`, `macd`, `dual_ema`; ops `and`/`or`/`vote` + case aliases; expose each leaf’s registry ParamDef names/types/bounds for bind + later 019 BNF (no BNF file in 016) per research.md R5–R6 and FR-002
- [x] T006 [P] Unit tests for catalogue allow-lists, ParamDef metadata exposure, and error code constants in `backend/tests/unit/test_torque_bind_catalogue.py`

**Checkpoint**: Errors + catalogue ready; no bind/evaluate yet

---

## Phase 3: User Story 1 - Check and bind a phenotype (Priority: P1) — bind foundation

**Goal**: Operator/developer can `torque.check` a phenotype and bind it to a `Strategy` (leaf or composite) with fail-closed unknown leaf / bad form / bad params — before any Backtest run. (Product MVP = US1 + US2; this phase alone is not DONE.)

**Independent Test**: Valid `rsi(period=14)` binds; `and(rsi(...), macd(...))` binds; garbage text → `invalid_torque_form`; `foo(period=1)` → `unknown_torque_leaf`; invalid params → `invalid_torque_params`; no `run_engine` invoked on failure.

### Tests for User Story 1

- [x] T007 [P] [US1] Unit tests for `check_phenotype` / `bind_phenotype` success and fail-closed codes in `backend/tests/unit/test_torque_bind_check_bind.py`

### Implementation for User Story 1

- [x] T008 [US1] Implement `check_phenotype` wrapping `torque.check` in `backend/app/torque_bind/bind.py` mapping FormError → `invalid_torque_form`
- [x] T009 [US1] Implement leaf bind: Instruction → `validate_and_materialize` via `app.strategy.registry` in `backend/app/torque_bind/bind.py` (keywords only)
- [x] T010 [US1] Implement composition node parse into BoundNode tree (children ≥2) in `backend/app/torque_bind/bind.py`
- [x] T011 [US1] Implement signal combinators `and` / `or` / `vote` and `CompositeStrategy` (`evaluate`, `min_history_candles`) in `backend/app/torque_bind/compose.py` per research.md R5
- [x] T012 [US1] Export public API `check_phenotype`, `bind_phenotype` from `backend/app/torque_bind/__init__.py`

**Checkpoint**: US1 fully functional — check+bind+compose without Backtest

---

## Phase 4: User Story 2 - Backtest a composed program (Priority: P1)

**Goal**: Bound phenotype runs through Feature 004 Backtest path; composition changes outcomes vs single leaf on a fixed fixture; replay is deterministic.

**Independent Test**: Same phenotype + fixture candles → identical `netProfit`; `and(rsi, macd)` metrics differ from bare `rsi` on a documented fixture in a controlled way; intent still passes Controller→Risk inside `run_engine`.

### Tests for User Story 2

- [x] T013 [P] [US2] Integration tests in `backend/tests/integration/test_torque_backtest_evaluate.py`: fixture candles + `run_bound_backtest` (or bind + `run_engine`) replay identical `netProfit`; composition vs leaf differs; assert Feature 004 path still applies Controller→Risk (engine invariants or journal/reject). Do **not** require full `evaluate_phenotype` contract shape (that is US3)

### Implementation for User Story 2

- [x] T014 [US2] Implement internal Backtest wire `run_bound_backtest` (name may vary) that takes a bound `Strategy` / phenotype+bind and calls Feature 004 `run_engine` (or equivalent) in `backend/app/torque_bind/evaluate.py` — return raw metrics needed for SC-002/SC-003; leave public `evaluate_phenotype` envelope to T018
- [x] T015 [US2] Ensure strategy modules remain auto-registered before evaluate (reuse existing `app.main` / strategy imports; document in evaluate module if import hook required)
- [x] T016 [US2] Add fixture candle builder or reuse existing backtest fixtures under `backend/tests/` for US2/US3 shared data

**Checkpoint**: US1 + US2 — product MVP: composed programs Backtest successfully

---

## Phase 5: User Story 3 - Evaluate API for UGE (Priority: P2)

**Goal**: Public `evaluate_phenotype(source, …) → TorqueEvaluateResult` wrapping the US2 Backtest wire, with metrics suitable for Feature 019 fitness; stable failure envelope; no secrets/live keys required.

**Independent Test**: Success shape includes `metrics.netProfit` and `effectiveLeaves`; failure returns `ok=false` + stable code; Strategy/Controller/Risk do not import FORGE; torque_bind does not import Real place path.

**016 DONE for US3**: Python API + T017 tests. HTTP (T020–T021) is optional and **non-blocking**.

### Tests for User Story 3

- [x] T017 [P] [US3] Unit/contract tests for `evaluate_phenotype` success/failure shapes and import guards in `backend/tests/unit/test_torque_bind_evaluate.py`

### Implementation for User Story 3

- [x] T018 [US3] Implement `evaluate_phenotype` wrapping T014 `run_bound_backtest`, returning metrics (`netProfit`, optional `totalReturn`/`tradeCount`/`buyAndHoldNetProfit`, `effectiveLeaves`) in `backend/app/torque_bind/evaluate.py` per contracts/torque-bind-api.md
- [x] T019 [US3] Export `evaluate_phenotype` from `backend/app/torque_bind/__init__.py`
- [ ] T020 [P] [US3] OPTIONAL (non-blocking for DONE): smoke routes `POST /torque/check` and `POST /torque/evaluate` in `backend/app/api/torque.py` mounted from `backend/app/main.py`
- [ ] T021 [P] [US3] OPTIONAL (only if T020 done): proxy `/torque` in `frontend/vite.config.ts` (no UI required)

**Checkpoint**: US3 Python evaluate ready for 019; HTTP optional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, safety, quickstart validation

- [x] T022 [P] Confirm no FORGE source trees vendored under repo; only docs path references in `docs/FORGE_INTEGRATION.md`
- [x] T023 [P] Update `specs/016-torque-trading-program/quickstart.md` with exact pytest module names once present
- [x] T024 Run quickstart automated gates (`pytest` for torque_bind unit + integration) from `backend/`
- [x] T025 [P] Update ROADMAP Feature 016 status only after implement complete and T024 green (do not mark DONE in this tasks-only step)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Depends on US1 bind/compose (T008–T012)
- **US3 (Phase 5)**: Depends on US2 evaluate path (T014–T016) for real metrics
- **Polish (Phase 6)**: Depends on US1–US3 complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2/US3
- **US2 (P1)**: Needs US1 bind + CompositeStrategy
- **US3 (P2)**: Needs US2 Backtest wire for real metrics

### Parallel Opportunities

- T002 parallel T003 after T001
- T005 parallel T006 after T004
- T017 parallel T020/T021 after evaluate core
- T022 parallel T023 in polish

---

## Parallel Example: User Story 1

```bash
# After Foundational:
Task: "Unit tests for check/bind in backend/tests/unit/test_torque_bind_check_bind.py"
Task: "Implement check_phenotype wrapping torque.check in backend/app/torque_bind/bind.py"
# Then sequentially: leaf bind → composition tree → compose.py → exports
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (check + bind + compose) — validate fail-closed
4. Complete Phase 4: US2 (`run_bound_backtest` + fixture gates) — **product MVP**
5. Continue US3 for public `evaluate_phenotype` (thin wrapper; ship same pass if cheap)

### Incremental Delivery

1. Setup + Foundational → catalogue + ParamDef metadata ready
2. US1 → check/bind demo
3. US2 → Backtest composed phenotype (core product proof / 016 MVP)
4. US3 → `evaluate_phenotype` for UGE handoff (HTTP optional, non-blocking)
5. Polish → quickstart green

### Suggested MVP scope

**US1 + US2** (check/bind + Backtest composition). US3 Python `evaluate_phenotype` is thin once US2 exists and should ship in the same implement pass when possible. Skip T020–T021 unless operator wants HTTP smoke.

### 016 DONE criteria (aligned with research R7/R9)

- Required: T001–T019 path green (or equivalent: bind + `run_bound_backtest` + `evaluate_phenotype` + tests T007/T013/T017)
- Required: T022–T024 safety/quickstart gates
- Not required: T020–T021 HTTP/proxy
- Not required: Feature 003 Simulation wiring
- T025 ROADMAP DONE only after gates green

---

## Notes

- [P] = different files, no incomplete dependencies
- Do not implement Feature 019 UGE loop or BNF grammar file here
- Do not enable Real / place orders
- Commit only when the operator asks
