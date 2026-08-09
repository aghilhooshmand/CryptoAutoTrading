# Tasks: Simulation Trading Core

**Input**: Design documents from `/specs/003-simulation-trading-core/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — Constitution XXVIII and plan/research Decision 10 require trading-critical automated tests (accounting, pipeline, stops, journals, recovery).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Spec precedence**: Latest `spec.md` clarifications override older plan wording where they differ:
`allocated_capital ≤ starting_capital`, `max_position_size ≤ allocated_capital`,
manual stop uses forced-close rules, Decision Journal records HOLD on every
closed-candle evaluation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `README.md` at repository root; feature docs under `specs/003-simulation-trading-core/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add simulation package layout, SQLAlchemy dependency, DB path, Vite proxy (no trading behavior yet)

- [ ] T001 Create backend package dirs `backend/app/simulation/`, `backend/app/simulation/strategy/`, `backend/app/simulation/control/`, `backend/app/simulation/execution/`, `backend/app/db/`, and ensure `backend/tests/unit/`, `backend/tests/contract/`, `backend/tests/integration/` exist per plan.md
- [ ] T002 [P] Create frontend dirs `frontend/src/features/simulation/` per plan.md
- [ ] T003 [P] Add runtime `sqlalchemy` dependency in `backend/pyproject.toml` (keep pytest/httpx dev extras intact)
- [ ] T004 [P] Ensure `backend/data/` exists for default SQLite file and add `backend/data/` (or `*.db`) to `.gitignore`
- [ ] T005 Extend Vite proxy in `frontend/vite.config.ts` to forward `/simulation` (keep `/health` and `/market`) to `http://127.0.0.1:8000`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: SQLite domain store, clock, money/accounting/sizing/state machine, execution port, recovery lifespan, session service skeleton, and typed frontend API client — required before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Implement `Clock` protocol with `SystemClock` and `FakeClock` in `backend/app/simulation/clock.py`
- [ ] T007 [P] Implement decimal/rate helpers in `backend/app/simulation/money.py` (fraction rates; fee/slippage defaults `0.001` / `0.0005`)
- [ ] T008 [P] Implement fill math, mark equity, liquidation equity, and Session NET helpers in `backend/app/simulation/accounting.py` per research (no double-count of hyp. exit costs)
- [ ] T009 [P] Implement full-BUY sizing `min(current_cash/(1+fee_rate), allocated_capital, max_position_size)` in `backend/app/simulation/position_sizing.py`
- [ ] T010 [P] Implement session state transitions `CONFIGURED → RUNNING → STOPPING → STOPPED` in `backend/app/simulation/state_machine.py`
- [ ] T011 [P] Define `ExecutionEngine` protocol in `backend/app/simulation/execution/port.py` and `SimulationExecutionEngine` only in `backend/app/simulation/execution/simulation.py` (reject real_money at API later; no real-money engine module)
- [ ] T012 Configure SQLite engine/session factory and `SIMULATION_DB_PATH` in `backend/app/db/session.py`
- [ ] T013 Define SQLAlchemy tables for sessions, decision journal, trade journal in `backend/app/db/models.py` per data-model.md (include `strategy_fill_count`, profit/loss **rates and amounts**, flatten status, `last_processed_candle_open_time`)
- [ ] T014 Implement startup recovery `RUNNING|STOPPING → STOPPED` with `backend_restart` and `unsafe_unflattened` when long (no auto-flatten) in `backend/app/simulation/recovery.py`
- [ ] T015 Wire FastAPI lifespan in `backend/app/main.py`: create tables, run recovery, keep `/health` and `/market` working
- [ ] T016 Implement session create/validation skeleton in `backend/app/simulation/session_service.py` enforcing `allocated_capital ≤ starting_capital`, `max_position_size ≤ allocated_capital`, derive/store profit/loss amounts from rates, reject `mode=real_money`, defaults for fee/slippage
- [ ] T017 [P] Add package markers `backend/app/simulation/__init__.py`, `strategy/__init__.py`, `control/__init__.py`, `execution/__init__.py`, `backend/app/db/__init__.py`
- [ ] T018 [P] Create typed frontend client `frontend/src/services/simulationApi.ts` for `/simulation/*` per `specs/003-simulation-trading-core/contracts/simulation-api.md`
- [ ] T019 [P] Add unit tests for accounting (mark vs liquidation; no double-count) in `backend/tests/unit/test_accounting.py`
- [ ] T020 [P] Add unit tests for position sizing bounds in `backend/tests/unit/test_position_sizing.py`
- [ ] T021 [P] Add unit tests for state machine + recovery in `backend/tests/unit/test_state_machine.py` and `backend/tests/unit/test_recovery.py`

**Checkpoint**: Foundation ready — DB/recovery/clock/accounting/sizing exist; frontend can call typed client; no XT types in simulation package

---

## Phase 3: User Story 1 - Configure and start one simulation session (Priority: P1) 🎯 MVP

**Goal**: Operator configures and starts exactly one SIMULATION session with nested capital bounds, % profit/loss (UI shows % and USDT), unmistakable simulation labeling; real-money unavailable.

**Independent Test**: Configure valid bounds for a supported pair, start session, see SIMULATION label and `RUNNING`; second start refused; invalid capital nesting blocked; no XT trading credentials required.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US1] Contract tests for `POST /simulation/sessions`, `POST .../start`, `GET .../active` (validation, `real_money_unavailable`, `session_already_active`, derived amounts) in `backend/tests/contract/test_simulation_api.py`
- [ ] T023 [P] [US1] Frontend tests for config validation display (allocated ≤ starting, max size ≤ allocated, % + amount) in `frontend/src/__tests__/simulationConfig.test.tsx`

### Implementation for User Story 1

- [ ] T024 [US1] Implement create/start/active/get session HTTP routes in `backend/app/api/simulation.py` per contracts; mount router in `backend/app/main.py`
- [ ] T025 [US1] Complete `session_service.py` create/start/get/active: one active session, derive `targetNetProfitAmount`/`maxSessionLossAmount`, set `cash=starting_capital`, state transitions
- [ ] T026 [P] [US1] Implement `SimulationBadge.tsx` (clear SIMULATION labeling) in `frontend/src/features/simulation/SimulationBadge.tsx`
- [ ] T027 [US1] Implement `SessionConfigForm.tsx` collecting pair, starting/allocated capital, max position size, profit/loss **rates** with live derived USDT amounts, max trades, duration, timeframe, optional fee/slippage overrides
- [ ] T028 [US1] Implement `SessionStatusPanel.tsx` + `useSimulationSession.ts` for create/start/active polling/status
- [ ] T029 [US1] Replace Auto Trading placeholder in `frontend/src/pages/AutoTradingPage.tsx` with config/start/status UI; ensure real-money controls unavailable/non-functional
- [ ] T030 [US1] Run T022–T023 tests and fix until passing; smoke create/start from quickstart scenario 1

**Checkpoint**: MVP — one simulation session can be configured and started with clear SIMULATION labeling

---

## Phase 4: User Story 2 - Controlled pipeline market data → simulated execution (Priority: P1)

**Goal**: Closed-candle dual EMA(9)/EMA(21) signals; Controller + Risk gate; simulation fills only; HOLD journals with no balance change; duplicate candle prevention; Feature 002 market boundary only.

**Independent Test**: With active session + FakeClock/safe data, observe HOLD (journaled, no fill) and at least one approved or rejected non-HOLD path that never bypasses control/risk.

### Tests for User Story 2

- [ ] T031 [P] [US2] Unit tests for dual EMA crossover + warm-up HOLD in `backend/tests/unit/test_dual_ema.py`
- [ ] T032 [P] [US2] Unit tests for duplicate-candle guard in `backend/tests/unit/test_duplicate_candle.py`
- [ ] T033 [P] [US2] Unit tests for risk/controller rejects (BUY while long, SELL while flat, stale data) in `backend/tests/unit/test_risk_rejects.py`
- [ ] T034 [P] [US2] Integration test for pipeline with FakeClock + fake market data in `backend/tests/integration/test_simulation_pipeline.py`

### Implementation for User Story 2

- [ ] T035 [P] [US2] Implement Strategy protocol in `backend/app/simulation/strategy/base.py` and dual EMA(9)/EMA(21) in `backend/app/simulation/strategy/dual_ema.py` (closed closes only)
- [ ] T036 [P] [US2] Implement Trading Controller in `backend/app/simulation/control/controller.py`
- [ ] T037 [P] [US2] Implement Risk Manager in `backend/app/simulation/control/risk.py` (long-only full position, limits, stale/unsafe quote using Feature 002 60s safety)
- [ ] T038 [US2] Implement `SimulationExecutionEngine` fills (adverse slippage, fees, cash/position updates, trade journal row, strategy_fill_count) in `backend/app/simulation/execution/simulation.py`
- [ ] T039 [US2] Implement pipeline orchestration (MD via Feature 002 service only → strategy → control → risk → exec; Decision Journal for HOLD/approve/reject) in `backend/app/simulation/pipeline.py`
- [ ] T040 [US2] Implement RUNNING worker loop (poll closed candles via Clock; process newest closed bar once; persist `last_processed_candle_open_time`) in `backend/app/simulation/worker.py`; start/stop worker from session_service on RUNNING/STOPPED
- [ ] T041 [US2] Ensure simulation code imports only normalized `market_data` models/service — never XT adapter types — across `pipeline.py` / `worker.py` / `risk.py`
- [ ] T042 [US2] Run T031–T034 tests and fix until passing

**Checkpoint**: Closed-candle pipeline executes simulated trades only through controller/risk

---

## Phase 5: User Story 3 - Journals, balances, and NET session P&L (Priority: P1)

**Goal**: Inspect Decision Journal (incl. HOLD), Trade Journal, balances/position, distinct gross/fees/slippage/net (liquidation NET for limits; mark informational).

**Independent Test**: After activity with ≥1 HOLD, ≥1 rejection, and ≥1 fill, journals and economics show consistent distinguishable fields.

### Tests for User Story 3

- [ ] T043 [P] [US3] Extend contract tests for `GET .../decisions`, `GET .../trades`, session economics fields in `backend/tests/contract/test_simulation_api.py`
- [ ] T044 [P] [US3] Frontend tests that economics distinguish net vs mark fields and journals render in `frontend/src/__tests__/simulationJournals.test.tsx`

### Implementation for User Story 3

- [ ] T045 [US3] Add decisions/trades/economics query methods in `backend/app/simulation/session_service.py` and routes in `backend/app/api/simulation.py`
- [ ] T046 [P] [US3] Implement `DecisionJournal.tsx` in `frontend/src/features/simulation/DecisionJournal.tsx`
- [ ] T047 [P] [US3] Implement `TradeJournal.tsx` in `frontend/src/features/simulation/TradeJournal.tsx`
- [ ] T048 [US3] Implement `EconomicsPanel.tsx` showing gross, fees, slippage, liquidation `netPnl`, mark equity/unrealized, rates+amounts, trade/strategy fill counts
- [ ] T049 [US3] Wire journals/economics into `AutoTradingPage.tsx` / `useSimulationSession.ts`
- [ ] T050 [US3] Optionally expose thin recent-session summary only on `frontend/src/pages/PortfolioPage.tsx` (not a full portfolio product)
- [ ] T051 [US3] Run T043–T044 tests and fix until passing

**Checkpoint**: Journals and economics are inspectable and consistent with accounting rules

---

## Phase 6: User Story 4 - Hard stops, manual stop, and emergency stop (Priority: P1)

**Goal**: Profit/max-loss via liquidation NET vs derived amounts; max_trades (strategy fills + one forced close exception); duration; emergency; manual stop; unsafe data; forced close when safe else unsafe_unflattened; no new strategy exec after stop.

**Independent Test**: Trigger each stop class in tests; confirm STOPPED, journals, and zero further strategy fills; forced close marked `is_forced_close`.

### Tests for User Story 4

- [ ] T052 [P] [US4] Unit tests for forced close + unsafe_unflattened + no double-count in `backend/tests/unit/test_forced_close.py`
- [ ] T053 [P] [US4] Unit tests for max_trades strategy cap with one forced-close overflow in `backend/tests/unit/test_max_trades.py`
- [ ] T054 [P] [US4] Contract/integration tests for stop, emergency-stop, profit/loss/duration stops in `backend/tests/contract/test_simulation_api.py` and/or `backend/tests/integration/test_simulation_pipeline.py`

### Implementation for User Story 4

- [ ] T055 [US4] Implement limit evaluation (liquidation NET vs stored amounts; duration; max strategy fills) in `backend/app/simulation/session_service.py` / `worker.py` / `risk.py`
- [ ] T056 [US4] Implement stop / emergency-stop / manual-stop paths: `RUNNING → STOPPING → STOPPED`, shared forced-close helper (safe price → fill+journal `is_forced_close`; else `unsafe_unflattened`) including **manual stop**
- [ ] T057 [US4] Add `POST .../stop` and `POST .../emergency-stop` routes in `backend/app/api/simulation.py`
- [ ] T058 [US4] Add Stop and Emergency Stop controls to `SessionStatusPanel.tsx` / `AutoTradingPage.tsx` with clear SIMULATION context
- [ ] T059 [US4] Enforce no new strategy-driven execution after STOPPING/STOPPED; worker exits cleanly
- [ ] T060 [US4] Run T052–T054 tests and fix until passing; validate quickstart hard-stop scenarios

**Checkpoint**: All stop authorities enforceable; forced close rules consistent

---

## Phase 7: User Story 5 - Phone and desktop Auto Trading monitoring (Priority: P2)

**Goal**: Primary configure/start/status/stop/emergency-stop and core status usable at ~375px.

**Independent Test**: At ~375px width, complete primary session controls without desktop-only gestures.

### Tests for User Story 5

- [ ] T061 [P] [US5] Frontend responsive/smoke tests for primary Auto Trading controls at narrow viewport in `frontend/src/__tests__/simulationResponsive.test.tsx`

### Implementation for User Story 5

- [ ] T062 [US5] Adjust Auto Trading simulation layout/CSS so config, status, economics entry, journals entry, stop, and emergency-stop remain usable at ~375px in `frontend/src/pages/AutoTradingPage.tsx` and related feature components
- [ ] T063 [US5] Run T061 and fix until passing; manual check SC-009

**Checkpoint**: Phone-width supervision usable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Docs, end-to-end quickstart, scope guardrails

- [ ] T064 [P] Update root `README.md` with simulation quickstart pointers (no credentials; SQLite path; `/auto-trading`)
- [ ] T065 [P] Sync `specs/003-simulation-trading-core/research.md`, `data-model.md`, `contracts/simulation-api.md`, and `quickstart.md` validation notes with latest spec clarifications (capital nesting, manual stop flatten, HOLD journal) if any wording still lags
- [ ] T066 Run full backend `pytest` and frontend test suite; fix regressions
- [ ] T067 Walk `specs/003-simulation-trading-core/quickstart.md` scenarios 1–7 locally and record any gaps as fixes
- [ ] T068 Review deliverable for out-of-scope leaks (real XT trading APIs, WebSockets, multi-session, multi-strategy, sentiment, real-money engine) per FR-022 / SC-007–SC-008

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After Foundational; practically after US1 create/start exists to drive a RUNNING session
- **US3 (Phase 5)**: After US2 produces journals/fills (can stub reads earlier, but independent test needs US2 activity)
- **US4 (Phase 6)**: After US2 pipeline + US1 session controls; shares stop UI with US1 surfaces
- **US5 (Phase 7)**: After US1–US4 UI exists to restyle
- **Polish (Phase 8)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — MVP session configure/start
- **US2 (P1)**: Needs US1 session lifecycle to attach worker; independently testable with FakeClock
- **US3 (P1)**: Needs US2 decision/trade writes for full independent test
- **US4 (P1)**: Needs US2 execution + US1 session APIs
- **US5 (P2)**: Needs Auto Trading UI from prior stories

### Parallel Opportunities

- Phase 1: T002–T004 parallel after T001 dirs started
- Phase 2: T006–T011, T017–T021 largely parallel once package dirs exist; T012→T013→T014→T015 sequential-ish
- US1: T022–T023 parallel; T026 parallel with backend T024–T025
- US2: T031–T034 and T035–T037 parallel
- US3: T046–T047 parallel
- US4: T052–T054 parallel

---

## Parallel Example: User Story 2

```bash
# Tests in parallel:
Task: "Unit tests for dual EMA in backend/tests/unit/test_dual_ema.py"
Task: "Unit tests for duplicate-candle in backend/tests/unit/test_duplicate_candle.py"
Task: "Unit tests for risk rejects in backend/tests/unit/test_risk_rejects.py"

# Implementation in parallel (after tests failing):
Task: "Strategy dual_ema.py"
Task: "controller.py"
Task: "risk.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: create/start one SIMULATION session, capital nesting, % + amount UI
5. Continue US2+ for a demoable trading machine

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → configure/start MVP
3. US2 → closed-candle simulated pipeline
4. US3 → journals + economics
5. US4 → stops + forced close
6. US5 → phone UX
7. Polish → docs + quickstart + scope review

### Suggested MVP scope

**US1 only** (configure/start one simulation session). Full Feature 003 acceptance needs US1–US4 at minimum; US5 for SC-009.

---

## Notes

- [P] = different files, no incomplete-task dependencies
- No real-money execution module in Feature 003 — reject at API/session boundary
- Market data only via Feature 002 normalized boundary
- Commit after each task or logical group when the user requests commits
- Format validation: all tasks use `- [ ] Txxx ...` with file paths; story tasks include `[USn]`
