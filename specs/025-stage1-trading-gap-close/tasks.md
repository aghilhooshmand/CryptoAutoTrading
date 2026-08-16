# Tasks: Stage-1 Trading Gap-Close

**Input**: Design documents from `/specs/025-stage1-trading-gap-close/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required — FR-018 / SC-001–SC-008 (TP, SL, strategy exit, same-candle
precedence, disabled TP/SL, invalid config, repeated cycles accounting, new
strategies, UI visibility). Prefer fixtures/mocks; no Real XT; no ticks.

**Organization**: Extend existing Simulation, Backtest, and Strategy packages
only. Propose commits only; do not auto-commit. Keep Feature 025 `IN PROGRESS`
on `docs/ROADMAP.md` until polish acceptance; mark `DONE` only after MVP-1 gate.

**Spec locks** (must hold through all tasks):
- Single pipeline; no second engine; no Real / Torque / GE (FR-001, FR-017)
- Never invent prices/fills; TP/SL trigger ≠ fill price (FR-003, FR-005, Q4)
- % only config; derive absolute levels from entry fill (FR-004, Q3)
- High→TP / Low→SL; never on entry-fill candle; SL wins if both (FR-005–006, Q1/Q5)
- No mid-position TP/SL edits (FR-004, FR-007, Q6)
- Session/emergency stops before SL before TP before strategy (FR-006)
- Protective TP/SL exits are forced/safety-style: do **not** increment `strategyFillCount` / consume `maxTrades` (FR-009; `contracts/protective-exits.md`)
- Sim mark vs Backtest next-open intentional; document, don’t unify (FR-012, R7)
- OHLC strategy bars; volume strategy deferred (FR-013–014, R5–R6)
- Minimal UI; ~375px; no Portfolio redesign (FR-016)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US5 map to spec stories

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/025-stage1-trading-gap-close/`, `docs/ROADMAP.md`, `README.md`

---

## Phase 1: Setup

**Purpose**: Align docs and confirm touch points; no behavior change yet

- [X] T001 Verify Feature 025 is `IN PROGRESS` on `docs/ROADMAP.md` and branch is `025-stage1-trading-gap-close`; confirm no Real/014-expansion scope creep
- [X] T002 [P] Add brief Feature 025 operator notes to `README.md` (per-position TP/SL %; Sim vs Backtest fill differences pointer to `specs/025-stage1-trading-gap-close/contracts/sim-vs-backtest-semantics.md`; no Real trading) without inventing undocumented APIs

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Schema, shared TP/SL helpers, OHLC candle contract, and API field
plumbing required by all stories

**⚠️ CRITICAL**: No user-story TP/SL pipeline work until this phase completes

- [X] T003 Extend `SimulationSessionRow`, `BacktestRunRow`, and `OperatorDefaultsRow` in `backend/app/db/models.py` with nullable `take_profit_percent` and `stop_loss_percent`; on `SimulationSessionRow` also add nullable `take_profit_price`, `stop_loss_price`, `entry_fill_candle_open_time` per `data-model.md`; add `_ensure_column` calls in `backend/app/db/session.py` `init_db()`
- [X] T004 [P] Implement shared TP/SL helpers in `backend/app/execution/tpsl.py` (validate percents; derive absolute long levels from entry fill; trigger predicate high/low with entry-bar skip; SL-before-TP; stable reason codes `take_profit` / `stop_loss`) per `contracts/protective-exits.md` and research R1–R3
- [X] T005 Extend strategy bar type in `backend/app/strategy/base.py` to OHLC (`open`, `high`, `low`, `close`, `open_time`); keep existing five strategies close-based-compatible; update re-exports in `backend/app/strategy/__init__.py` / `backend/app/simulation/strategy/` as needed
- [X] T006 [P] Unit tests for `backend/app/execution/tpsl.py` in `backend/tests/unit/test_tpsl.py` (derive levels; entry-bar skip; SL wins; disabled sides; invalid percents)
- [X] T007 Wire create/validate + `session_to_dict` TP/SL % and absolute fields in `backend/app/simulation/session_service.py` (reject invalid config; expose `takeProfitPercent`, `stopLossPercent`, `entryFillPrice`, `takeProfitPrice`, `stopLossPrice`); clear absolute levels on flat/SELL
- [X] T008 [P] Wire Backtest `validate_config` / create persistence for `takeProfitPercent` / `stopLossPercent` on `BacktestRunRow` via `backend/app/backtest/service.py` (mirror session risk rate fields; pass percents into `run_engine`) per `contracts/protective-exits.md`
- [X] T009 [P] Optional operator defaults fields for TP/SL % on `OperatorDefaultsRow` + settings API (`backend/app/settings/` + related) without Settings architecture redesign — omit UI until US5 if backend-only first

**Checkpoint**: Schema + helpers + OHLC type + config plumbing ready; pipelines unchanged until US1

---

## Phase 3: User Story 1 - Attach TP/SL and exit by protective levels (Priority: P1) 🎯 MVP

**Goal**: Optional per-position TP/SL exits work in Simulation and Backtest through Controller → Risk → Execution with mode-native fills

**Independent Test**: Configure TP and/or SL; open long; process candles that cross levels after entry bar; assert protective exit reason and fill not at TP/SL price — in both modes

### Tests for User Story 1

- [X] T010 [P] [US1] Unit/pipeline tests for Simulation protective TP and SL in `backend/tests/unit/test_protective_exits_simulation.py` (or extend `backend/tests/integration/test_simulation_pipeline.py`): entry-bar skip; high→TP; low→SL; fill uses mark not level; disabled sides
- [X] T011 [P] [US1] Unit/engine tests for Backtest protective TP and SL in `backend/tests/unit/test_protective_exits_backtest.py` (or `backend/tests/integration/test_backtest_protective_exits.py`): next-open fill; no next candle fail-closed path; entry-bar skip

### Implementation for User Story 1

- [X] T012 [US1] Build OHLC strategy/lookback candles from market `Candlestick` in `backend/app/simulation/pipeline.py` (stop dropping high/low)
- [X] T013 [US1] On BUY fill in Simulation path (`pipeline.py` / session apply-fill), set `entry_fill_price`, `entry_fill_candle_open_time`, derive absolute TP/SL via `execution/tpsl.py`; clear on close
- [X] T014 [US1] Evaluate protective TP/SL after session hard-stops and before strategy in `backend/app/simulation/pipeline.py`; emit protective SELL through Controller → Risk → Execution (live mark); record `take_profit` / `stop_loss` reasons; never fill at trigger level
- [X] T015 [US1] Mirror TP/SL derive + evaluate + next-open protective SELL in `backend/app/backtest/engine.py` (and pass % into engine state from `backend/app/backtest/service.py`)
- [X] T016 [US1] Ensure API/create contract fields documented by `contracts/protective-exits.md` are covered by contract or service tests in `backend/tests/contract/` (create reject invalid TP/SL; status shows levels while long)

**Checkpoint**: US1 MVP — Backtest and Simulation can exit by TP or SL correctly

---

## Phase 4: User Story 2 - Strategy exit with TP/SL precedence (Priority: P1)

**Goal**: Strategy SELL still works; same-candle precedence SL > TP > strategy; repeated cycles keep accounting correct

**Independent Test**: Long with TP/SL; strategy SELL before levels; SL+strategy same candle; TP+SL same candle; ≥3 BUY/exit cycles with correct cash/holdings

### Tests for User Story 2

- [X] T017 [P] [US2] Precedence and cycle tests in `backend/tests/unit/test_protective_exit_precedence.py` (SL vs TP; SL vs strategy; session hard-stop still first; repeated cycles accounting; protective exit does not increment `strategyFillCount`)

### Implementation for User Story 2

- [X] T018 [US2] Enforce evaluation order in `backend/app/simulation/pipeline.py` and `backend/app/backtest/engine.py`: session/emergency stops → SL → TP → strategy; single closing fill per candle
- [X] T019 [US2] Align protective-exit journal/trade flags with forced/safety closes in Simulation session apply-fill and Backtest `_apply_strategy_fill`: use forced-style closes (`is_forced=True` / equivalent) so TP/SL exits do **not** increment `strategyFillCount` or consume `maxTrades`; keep reasons `take_profit` / `stop_loss` distinct (FR-009; `contracts/protective-exits.md` maxTrades lock)

**Checkpoint**: US2 — precedence and multi-cycle accounting green

---

## Phase 5: User Story 3 - Document intentional Sim vs Backtest differences (Priority: P1)

**Goal**: Operators can see intentional fill differences; accidental TP/SL/strategy/risk semantic gaps are fixed

**Independent Test**: Read semantics note; run shared-config fixtures asserting rule parity with intentional fill divergence only

### Tests for User Story 3

- [X] T020 [P] [US3] Regression tests in `backend/tests/unit/test_sim_backtest_tpsl_parity.py` asserting identical TP/SL trigger outcomes for identical OHLC+levels while allowing different fill prices per mode

### Implementation for User Story 3

- [X] T021 [US3] Ensure `specs/025-stage1-trading-gap-close/contracts/sim-vs-backtest-semantics.md` is accurate vs implementation; add README pointer (T002) if missing
- [X] T022 [US3] Resolve failures from T020 and any checklist gaps vs `contracts/sim-vs-backtest-semantics.md` (same TP/SL %→levels, high/low triggers, entry-bar skip, SL-before-TP, fees/slippage on fills, reason codes) without unifying Simulation mark vs Backtest next-open fill prices

**Checkpoint**: US3 — documented intentional differences; parity tests green

---

## Phase 6: User Story 4 - Bounded extra strategy primitives (Priority: P2)

**Goal**: Register Stochastic, Keltner/ATR channel, and ROC/Momentum; OHLC-aware; no volume strategy

**Independent Test**: `GET /strategies` includes three new ids; each produces deterministic signals under fixtures; existing five unchanged

### Tests for User Story 4

- [X] T023 [P] [US4] Unit tests for Stochastic in `backend/tests/unit/test_stochastic.py`
- [X] T024 [P] [US4] Unit tests for Keltner channel in `backend/tests/unit/test_keltner.py`
- [X] T025 [P] [US4] Unit tests for ROC/Momentum in `backend/tests/unit/test_roc_momentum.py`
- [X] T026 [P] [US4] Registry/contract assert new ids in `backend/tests/contract/test_strategies_api.py` (or extend existing strategies contract tests); assert volume strategy absent

### Implementation for User Story 4

- [X] T027 [P] [US4] Add ATR / stochastic helpers as needed in `backend/app/strategy/indicators.py`
- [X] T028 [P] [US4] Implement and register `stochastic` in `backend/app/strategy/stochastic.py`
- [X] T029 [P] [US4] Implement and register `keltner_channel` in `backend/app/strategy/keltner.py`
- [X] T030 [P] [US4] Implement and register `roc_momentum` in `backend/app/strategy/momentum_roc.py`
- [X] T031 [US4] Ensure Simulation + Backtest pass OHLC bars into `evaluate` (`pipeline.py`, `engine.py`) and import registrations via `backend/app/strategy/__init__.py`
- [X] T032 [US4] Confirm existing five strategies still close-based and regression-covered (extend existing strategy unit tests if needed)

**Checkpoint**: US4 — three new strategies selectable; volume deferred

---

## Phase 7: User Story 5 - Operator UI for TP/SL (Priority: P2)

**Goal**: Minimal UI for TP%/SL% on create and entry/absolute levels + exit reason while operating; usable ~375px

**Independent Test**: Create with TP/SL; see levels when long; see exit reason after protective/strategy exit; narrow viewport smoke

### Tests for User Story 5

- [X] T033 [P] [US5] Frontend tests for TP/SL fields and status display in `frontend/src/__tests__/` (e.g. session config + `SessionStatusPanel`; ~375px smoke following existing responsive patterns)

### Implementation for User Story 5

- [X] T034 [P] [US5] Extend types/API client in `frontend/src/services/simulationApi.ts` (and backtest client if separate) for TP/SL % and absolute level fields
- [X] T035 [US5] Add optional TP%/SL% inputs to `frontend/src/features/simulation/SessionConfigForm.tsx` and `frontend/src/features/backtest/BacktestConfigForm.tsx`
- [X] T036 [US5] Show `entryFillPrice`, absolute TP/SL, and exit/stop reason in `frontend/src/features/simulation/SessionStatusPanel.tsx` (no mid-position editors; no Portfolio redesign)
- [X] T037 [P] [US5] Optional defaults for TP%/SL% in `frontend/src/features/settings/SettingsPanel.tsx` / `mapSettingsToForm.ts` only if backend T009 landed — keep Settings change minimal

**Checkpoint**: US5 — operators can configure and observe TP/SL without redesign

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Gates, docs, freeze scope, ROADMAP

- [X] T038 [P] Assert RealExecutionAdapter still unavailable / no XT private trading introduced by Feature 025 in `backend/tests/unit/test_real_execution_stub.py` (or thin companion)
- [X] T039 [P] Update `specs/025-stage1-trading-gap-close/quickstart.md` if test paths drifted during implement
- [X] T040 Run Feature 025 pytest set from quickstart until green (`test_tpsl`, protective exit suites, new strategy tests, parity tests, contract creates)
- [X] T041 Run frontend Feature 025 tests until green
- [X] T042 Perform MVP-1 acceptance validation per spec FR-019 / quickstart §4 (Backtest → Simulation → BUY → TP/SL/strategy EXIT → accounting → history; 014 restart as-is); file only concrete defect follow-ups
- [X] T043 Mark Feature 025 `DONE` on `docs/ROADMAP.md` only after acceptance gates; leave commit proposal to operator (no auto-commit)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: After Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: After Foundational — **MVP**
- **US2 (Phase 4)**: After US1 protective path exists (extends same files)
- **US3 (Phase 5)**: After US1 (parity needs working TP/SL); can overlap late US2
- **US4 (Phase 6)**: After Foundational OHLC (T005); can parallel US1 if OHLC bars already fed — prefer after T012
- **US5 (Phase 7)**: After US1 status fields exist (T007/T013)
- **Polish (Phase 8)**: After desired stories complete

### User Story Dependencies

- **US1**: No dependency on US2–US5
- **US2**: Depends on US1 hooks
- **US3**: Depends on US1 semantics
- **US4**: Depends on OHLC foundational + evaluate wiring
- **US5**: Depends on API fields from Foundational/US1

### Parallel Opportunities

- T002 || T001 (setup)
- T004 || T005 after T003 started (helpers vs OHLC type)
- T006 || T008 || T009 after T004/T003
- T010 || T011 (US1 tests)
- T023 || T024 || T025 || T026 (US4 tests)
- T028 || T029 || T030 after T027
- T034 || T033 (US5)

---

## Parallel Example: User Story 1

```bash
# Tests first (expect fail before impl):
Task: T010 Simulation protective exit tests
Task: T011 Backtest protective exit tests

# Then implementation sequential on shared pipeline/engine:
Task: T012 OHLC lookback in pipeline
Task: T013 Derive levels on BUY
Task: T014 Protective evaluate in pipeline
Task: T015 Mirror in backtest engine
Task: T016 Contract create/status
```

---

## Parallel Example: User Story 4

```bash
Task: T023 test_stochastic.py
Task: T024 test_keltner.py
Task: T025 test_roc_momentum.py
Task: T026 strategies API contract

Task: T028 stochastic.py
Task: T029 keltner.py
Task: T030 momentum_roc.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup  
2. Phase 2 Foundational  
3. Phase 3 US1 (TP/SL Sim + Backtest)  
4. **STOP and VALIDATE** US1 independently  
5. Continue US2 → US3 → US4 → US5 → Polish  

### Incremental Delivery

1. Setup + Foundational → ready  
2. US1 → protective exits MVP  
3. US2 → precedence + cycles  
4. US3 → semantics trust  
5. US4 → strategy diversity  
6. US5 → operator UI  
7. Polish + MVP-1 gate → ROADMAP DONE  

### Notes

- Do not implement volume strategy  
- Do not expand Feature 014 recovery  
- Do not redesign Portfolio or Settings architecture  
- Protective fills must never use TP/SL absolute price as fill  
- Commit only when operator requests  

---

## Phase 9: Convergence

**Purpose**: Close gaps found by `/speckit-converge` against spec, plan, and
constitution (post-implement assessment). Do not rewrite earlier phases.

- [X] T044 CRITICAL: Route Backtest protective TP/SL closes through Controller → Risk → Historical Execution before flatten in `backend/app/backtest/engine.py` (mirror Simulation `_try_protective_exit`); keep next-open fill, forced/non-`strategyFillCount` semantics, and `take_profit`/`stop_loss` reasons — per FR-003, US1/AC1, Constitution III–IV, plan: Controller/Risk gate (`contradicts`)
- [X] T045 [P] Strengthen repeated-cycle accounting assertions in `backend/tests/unit/test_protective_exit_precedence.py` (and/or Backtest companion): after ≥3 BUY→protective-exit cycles, assert cash/holdings/P&L match applied fills and fees/slippage — per FR-011, SC-004, US2/AC4 (`partial`)
- [X] T046 [P] Add automated coverage that session hard-stops (profit target / max session loss / emergency) still evaluate before TP/SL on the same candle path in Simulation (and Backtest where applicable) — per FR-006, FR-018, Edge Cases (`partial`)
