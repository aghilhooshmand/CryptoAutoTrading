# Tasks: Additional Strategies

**Input**: Design documents from `/specs/006-additional-strategies/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context and SC-001–SC-006 require golden fixtures, param validation, `S`/`S+1`, Dual EMA continuity regression, `GET /strategies` (5 entries), shared sim/backtest path, and UI selector coverage.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Spec precedence** (Session 2026-08-12 clarifications + plan):
- RSI / Bollinger: **recovery crossover** only (not level / not enter-zone)
- MACD: line/signal crossover; `S = slowPeriod + signalPeriod` (conventional bound)
- Breakout: **every new extreme** (trend-following continuation)
- History: backtest reject if count `< S`; HOLD until `S+1` (Dual EMA contract)
- Dual EMA behavior **unchanged**; continuity tests must pass unmodified
- No engine/API special-casing; register via existing registry
- No real money / optimization / ranking / ML / multi-strategy / sentiment / leverage / shorting
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/006-additional-strategies/`, root `README.md` only if needed

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm layout; no trading behavior yet

- [X] T001 Verify Feature 005 strategy package paths exist (`backend/app/strategy/`, `frontend/src/features/strategy/`, `frontend/src/services/strategiesApi.ts`) per plan.md
- [X] T002 [P] Confirm `backend/tests/unit/`, `backend/tests/contract/`, `backend/tests/integration/` are ready for new strategy test files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared indicator helpers and registration wiring — required before any user story strategy module

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T003 Implement Decimal helpers (EMA with Dual-EMA-compatible SMA seed + k=2/(n+1), SMA, population stdev, Wilder RSI series) in `backend/app/strategy/indicators.py` per research.md Decision 2–3
- [X] T004 [P] Unit tests for indicator helpers (EMA seed parity vs Dual EMA style, SMA, population σ, Wilder RSI warm-up Nones) in `backend/tests/unit/test_strategy_indicators.py`
- [X] T041 Extend `ParamDef` / `coerce_and_bounds` for `decimal_string` (parse Decimal, reject malformed, bounds + `exclusive_minimum`) in `backend/app/strategy/params.py`; expose `exclusiveMinimum` in `backend/app/strategy/registry.py` `to_api_list`
- [X] T042 [P] Unit tests for decimal_string preserve/reject/exclusive min in `backend/tests/unit/test_strategy_params.py`
- [X] T043 Frontend: `StrategyParamValue` number|string; decimal_string inputs preserve strings in payloads; client validates integers vs decimals + `exclusiveMinimum` in `frontend/src/services/strategiesApi.ts` and `frontend/src/features/strategy/StrategyConfigFields.tsx`; widen create types in `frontend/src/services/simulationApi.ts` and `frontend/src/services/backtestApi.ts`
- [X] T044 [P] Client constraint `oversold_lt_overbought` + decimal_string / exclusive-min tests in `frontend/src/__tests__/strategyConfig.test.tsx`
- [X] T005 Update `backend/app/strategy/__init__.py` (and `backend/app/main.py` if needed) so new strategy modules can be imported for auto-registration without changing Dual EMA registration
- [X] T006 Run existing Dual EMA continuity baseline: `pytest backend/tests/unit/test_dual_ema_continuity.py -q` must pass before adding strategies (FR-013 / SC-005 gate)

**Checkpoint**: Indicators ready; Dual EMA still green; story modules can register independently

---

## Phase 3: User Story 1 - Select RSI for simulation and backtest (Priority: P1) 🎯 MVP

**Goal**: Register RSI (`rsi`) with recovery-crossover signals, defaults 14/70/30, `S = period`; selectable in Simulation and Backtest via existing forms; Dual EMA untouched.

**Independent Test**: Create sim session with `strategyId: rsi` + defaults; persist effective params; golden fixture matches recovery BUY/SELL/HOLD; invalid oversold≥overbought rejected; same signal sequence in sim vs backtest path.

### Tests for User Story 1

- [X] T007 [P] [US1] Unit/golden tests for RSI recovery crossover, warm-up HOLD until `S+1`, param validation (oversold &lt; overbought) in `backend/tests/unit/test_rsi_strategy.py`
- [X] T008 [P] [US1] Contract tests: create sim/backtest with `rsi`; reject invalid RSI params; insufficient_history when candles &lt; `period` in `backend/tests/contract/test_simulation_api.py` and `backend/tests/contract/test_backtest_api.py` (extend)

### Implementation for User Story 1

- [X] T009 [US1] Implement and register RSI strategy (Wilder RSI, recovery crossover, `min_history_candles` = `period`) in `backend/app/strategy/rsi.py` per data-model.md / FR-001–FR-002
- [X] T010 [US1] Import `rsi` for auto-registration from `backend/app/strategy/__init__.py` (and `backend/app/main.py` if required)
- [X] T011 [P] [US1] Add RSI schema to `FALLBACK_STRATEGIES` in `frontend/src/services/strategiesApi.ts` per `contracts/additional-strategies-api.md`
- [X] T012 [P] [US1] Extend frontend strategy selector coverage for RSI defaults; assert oversold&lt;overbought uses client constraint `oversold_lt_overbought` (message: “Oversold threshold must be less than overbought threshold.”) in `frontend/src/__tests__/strategyConfig.test.tsx` (framework validation landed in T044; wire RSI into FALLBACK / selector here)
- [X] T013 [US1] Run T006–T008 and T012; fix until passing (Dual EMA continuity still green)

**Checkpoint**: RSI selectable end-to-end; MVP delivers second registered strategy

---

## Phase 4: User Story 2 - Select MACD for simulation and backtest (Priority: P1)

**Goal**: Register MACD (`macd`) with line/signal crossover, defaults 12/26/9, `S = slowPeriod + signalPeriod`.

**Independent Test**: Backtest with `strategyId: macd` defaults; golden fixture matches bullish/bearish crossovers; fast≥slow rejected; HOLD until `S+1`.

### Tests for User Story 2

- [X] T014 [P] [US2] Unit/golden tests for MACD crossover, warm-up, param validation (fast &lt; slow) in `backend/tests/unit/test_macd_strategy.py`
- [X] T015 [P] [US2] Contract tests: create with `macd`; reject invalid MACD params; insufficient_history when candles &lt; `slow+signal` in `backend/tests/contract/test_simulation_api.py` and `backend/tests/contract/test_backtest_api.py` (extend)

### Implementation for User Story 2

- [X] T016 [US2] Implement and register MACD strategy (shared EMA helpers, line/signal crossover, `S = slowPeriod + signalPeriod`) in `backend/app/strategy/macd.py` per FR-003–FR-004 / research Decision 4
- [X] T017 [US2] Import `macd` for auto-registration from `backend/app/strategy/__init__.py` (and `backend/app/main.py` if required)
- [X] T018 [P] [US2] Add MACD schema to `FALLBACK_STRATEGIES` in `frontend/src/services/strategiesApi.ts`
- [X] T019 [P] [US2] Extend frontend tests for MACD defaults / fast&lt;slow in `frontend/src/__tests__/strategyConfig.test.tsx`
- [X] T020 [US2] Run T014–T015 and T019; fix until passing (Dual EMA continuity still green)

**Checkpoint**: MACD available alongside Dual EMA and RSI

---

## Phase 5: User Story 3 - Select Bollinger Bands for simulation and backtest (Priority: P2)

**Goal**: Register Bollinger Bands (`bollinger_bands`) with SMA + population σ, recovery crossover through bands, defaults period 20 / `stdDev` `"2.0"`, `S = period`.

**Independent Test**: Simulation with `bollinger_bands`; BUY/SELL only on recovery crosses; level-outside stays HOLD; `stdDev ≤ 0` rejected; `decimal_string` params render in UI.

### Tests for User Story 3

- [X] T021 [P] [US3] Unit/golden tests for Bollinger recovery crossover, population σ, warm-up, stdDev validation in `backend/tests/unit/test_bollinger_strategy.py`
- [X] T022 [P] [US3] Contract tests: create with `bollinger_bands`; reject `stdDev` ≤ 0; insufficient_history when candles &lt; `period` in `backend/tests/contract/test_simulation_api.py` and `backend/tests/contract/test_backtest_api.py` (extend)

### Implementation for User Story 3

- [X] T023 [US3] Implement and register Bollinger Bands strategy (`stdDev` ParamDef with `exclusive_minimum=True`, `minimum=0`) in `backend/app/strategy/bollinger.py` per FR-005–FR-006 / research Decision 5 / T041
- [X] T024 [US3] Import `bollinger` for auto-registration from `backend/app/strategy/__init__.py` (and `backend/app/main.py` if required)
- [X] T025 [P] [US3] Add Bollinger schema (`stdDev` as `decimal_string` with `exclusiveMinimum: true`, `minimum: 0`, optional `std_dev_gt_zero` constraint) to `FALLBACK_STRATEGIES` in `frontend/src/services/strategiesApi.ts` per `contracts/additional-strategies-api.md`
- [X] T026 [P] [US3] **Required**: Frontend tests that Bollinger `stdDev` renders as `decimal_string`, client rejects `0` via exclusive minimum, and create payloads preserve strings such as `"2.0"` / `"1.5"` in `frontend/src/__tests__/strategyConfig.test.tsx` (uses T043 framework; must not coerce through `Number.isInteger`)
- [X] T027 [US3] Run T021–T022 and T026; fix until passing

**Checkpoint**: Mean-reversion Bollinger recovery strategy selectable

---

## Phase 6: User Story 4 - Select Breakout for simulation and backtest (Priority: P2)

**Goal**: Register Breakout (`breakout`) with every-new-extreme signals on prior lookback closes, default lookback 20, `S = lookback`.

**Independent Test**: Backtest with lookback 10; BUY on each new high beyond prior window; SELL on each new low; HOLD inside range; lookback &lt; 2 rejected.

### Tests for User Story 4

- [X] T028 [P] [US4] Unit/golden tests for Breakout every-new-extreme semantics, warm-up, lookback validation in `backend/tests/unit/test_breakout_strategy.py`
- [X] T029 [P] [US4] Contract tests: create with `breakout`; reject lookback &lt; 2; insufficient_history when candles &lt; lookback in `backend/tests/contract/test_simulation_api.py` and `backend/tests/contract/test_backtest_api.py` (extend)

### Implementation for User Story 4

- [X] T030 [US4] Implement and register Breakout strategy (prior window excludes current bar) in `backend/app/strategy/breakout.py` per FR-007–FR-008 / research Decision 6
- [X] T031 [US4] Import `breakout` for auto-registration from `backend/app/strategy/__init__.py` (and `backend/app/main.py` if required)
- [X] T032 [P] [US4] Add Breakout schema to `FALLBACK_STRATEGIES` in `frontend/src/services/strategiesApi.ts`
- [X] T033 [P] [US4] Extend frontend tests for Breakout defaults in `frontend/src/__tests__/strategyConfig.test.tsx`
- [X] T034 [US4] Run T028–T029 and T033; fix until passing

**Checkpoint**: All four new strategies registered and selectable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Catalog completeness, shared-path proof, Dual EMA regression, docs, non-mutation

- [X] T035 [P] Update `GET /strategies` contract tests to expect exactly 5 strategies with schemas from `contracts/additional-strategies-api.md` in `backend/tests/contract/test_strategies_api.py` (SC-001)
- [X] T036 [P] Extend integration test so Simulation and Backtest resolve the same class for at least one non–Dual-EMA id (e.g. `rsi`) in `backend/tests/integration/test_strategy_shared_sim_backtest.py`
- [X] T037 [P] Assert new strategies’ `evaluate` does not take/mutate balances (extend or add) in `backend/tests/unit/test_strategy_no_balance_mutation.py`
- [X] T038 Re-run Dual EMA continuity unmodified: `pytest backend/tests/unit/test_dual_ema_continuity.py -q` (SC-005)
- [X] T039 [P] Document Feature 006 strategy list in root `README.md` (link to `specs/006-additional-strategies/quickstart.md`)
- [X] T040 Run quickstart.md automated checks (backend unit/contract + frontend strategyConfig) and fix remaining failures

**Checkpoint**: Feature complete — five strategies, Dual EMA unchanged, quickstart green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Stories (Phases 3–6)**: All depend on Foundational
  - US1 (RSI) and US2 (MACD) are both P1 — prefer US1 first as MVP, then US2; can parallelize if staffed (different files)
  - US3 (Bollinger) and US4 (Breakout) after or parallel to P1 stories once foundation is done
- **Polish (Phase 7)**: Depends on all four user stories complete (especially T035 needing five registrations)

### User Story Dependencies

- **US1 RSI (P1)**: After Phase 2 — no dependency on other new strategies — **MVP**
- **US2 MACD (P1)**: After Phase 2 — independent of RSI (shares `indicators.py` only)
- **US3 Bollinger (P2)**: After Phase 2 — depends on T041–T044 decimal_string framework; T026 is mandatory
- **US4 Breakout (P2)**: After Phase 2 — independent

### Within Each User Story

- Tests (T007/T014/T021/T028) should fail before implementation where practical
- Implement strategy module → register import → FALLBACK → frontend test → run suite
- Do not modify Dual EMA algorithm or its continuity fixtures

### Parallel Opportunities

- T002 with T001
- T004 with T003 (tests can be written alongside helpers)
- Within a story: unit golden [P] + contract extend [P]; FALLBACK [P] + frontend test [P]
- Across stories (after Phase 2): US1–US4 strategy modules in different files can proceed in parallel
- Phase 7: T035, T036, T037, T039 can run in parallel after all strategies register

---

## Parallel Example: User Story 1 (RSI)

```bash
# After Phase 2, launch RSI tests together:
Task: "Unit/golden tests in backend/tests/unit/test_rsi_strategy.py"
Task: "Contract create/invalid/insufficient in test_simulation_api.py / test_backtest_api.py"

# After rsi.py registers:
Task: "FALLBACK RSI in frontend/src/services/strategiesApi.ts"
Task: "Frontend RSI coverage in frontend/src/__tests__/strategyConfig.test.tsx"
```

---

## Parallel Example: After Foundational (multi-story)

```bash
# Different developers / agents (different files):
Task: "Implement backend/app/strategy/rsi.py"
Task: "Implement backend/app/strategy/macd.py"
Task: "Implement backend/app/strategy/bollinger.py"
Task: "Implement backend/app/strategy/breakout.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 — RSI Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (indicators + Dual EMA baseline)
3. Complete Phase 3: RSI
4. **STOP and VALIDATE**: RSI selectable in sim/backtest; Dual EMA continuity green
5. Demo MVP (second strategy live)

### Incremental Delivery

1. Setup + Foundational → helpers ready
2. Add RSI → MVP
3. Add MACD → second P1 strategy
4. Add Bollinger → mean-reversion recovery
5. Add Breakout → trend-following extremes
6. Polish → five-strategy catalog, shared-path, docs, quickstart

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Phase 2:
   - Dev A: US1 RSI
   - Dev B: US2 MACD
   - Dev C: US3 Bollinger
   - Dev D: US4 Breakout
3. Merge registrations carefully in `__init__.py` / `FALLBACK_STRATEGIES`
4. One owner runs Phase 7 polish

---

## Notes

- [P] = different files, no incomplete dependencies
- [Story] maps to US1–US4 for traceability
- Do **not** refactor Dual EMA onto shared EMA unless continuity stays bit-identical (research Decision 2: leave Dual EMA local `_ema` by default)
- No new DB columns, routers, or hard-coded strategy field components
- Each story independently testable once its module is registered
- Stop at any checkpoint to validate without waiting for later stories
