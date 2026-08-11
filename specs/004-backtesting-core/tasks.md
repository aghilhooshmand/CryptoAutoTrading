# Tasks: Backtesting Core

**Input**: Design documents from `/specs/004-backtesting-core/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — Constitution XXVIII and plan Technical Context require trading-critical automated tests (fills, metrics, limits, determinism, contracts, pipeline). Spec success criteria SC-002–SC-006a are test-backed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Spec precedence**: Latest `spec.md` clarifications (Session 2026-08-11 + plan refinements) override older wording where they differ:
- Shared strategy/controller/risk/accounting; **HistoricalExecutionAdapter** for fills (not live simulation execution)
- Buy-and-hold starts at first executable candle in the **requested window**, independent of EMA warm-up
- Synchronous execution under **5000**-candle cap (v1)
- FIFO **20** completed + FIFO **5** failed; `approved_unexecutable` ≠ `rejected`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `README.md` at repository root; feature docs under `specs/004-backtesting-core/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout, Vite proxy, and package markers — no trading behavior yet

- [ ] T001 Create backend package dir `backend/app/backtest/` and ensure `backend/tests/unit/`, `backend/tests/contract/`, `backend/tests/integration/` exist per plan.md
- [ ] T002 [P] Create frontend dir `frontend/src/features/backtest/` per plan.md
- [ ] T003 [P] Add package marker `backend/app/backtest/__init__.py`
- [ ] T004 Extend Vite proxy in `frontend/vite.config.ts` to forward `/backtest` (keep `/health`, `/market`, `/simulation`) to `http://127.0.0.1:8000`
- [ ] T005 [P] Document `BACKTEST_DB_PATH` optional env (default beside simulation DB under `backend/data/`) in `backend/app/db/session.py` or settings helper without breaking Feature 003

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Feature 002 range candle fetch, history caps, SQLite backtest tables + repository retention, HistoricalExecutionAdapter fill primitives, service validation skeleton, typed frontend client — required before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Extend adapter protocol with optional `start_time`/`end_time` (UTC ms) in `backend/app/market_data/adapters/base.py`
- [ ] T007 Extend XT Spot adapter ranged kline fetch + pagination (XT `startTime`/`endTime` only inside adapter) in `backend/app/market_data/adapters/xt_spot.py`
- [ ] T008 Extend `MarketDataService.get_candles` to accept optional start/end and return normalized closed candles only in `backend/app/market_data/service.py`
- [ ] T009 [P] Implement `MAX_BACKTEST_CANDLES = 5000` estimate/reject helpers in `backend/app/backtest/limits.py`
- [ ] T010 [P] Add SQLAlchemy tables `backtest_runs`, `backtest_trades`, `backtest_decisions` in `backend/app/db/models.py` per `specs/004-backtesting-core/data-model.md`
- [ ] T011 Wire table create for backtest models in FastAPI lifespan / `backend/app/db/session.py` (reuse existing engine pattern; optional `BACKTEST_DB_PATH`)
- [ ] T012 Implement repository CRUD + deterministic FIFO retention (20 completed, 5 failed; cascade; tie-break by id) in `backend/app/backtest/repository.py`
- [ ] T013 [P] Implement HistoricalExecutionAdapter next-open / end-close fill math (fee + adverse slippage; shared `money`/`accounting`/`position_sizing`) in `backend/app/backtest/execution.py` — do **not** import live `simulation.execution.simulation` for fill timing
- [ ] T014 Implement config validation skeleton (capital nesting, window, timeframe, optional max_trades/profit/loss, defaults fee/slippage, oversized reject before fetch) in `backend/app/backtest/service.py`
- [ ] T015 [P] Create typed frontend client `frontend/src/services/backtestApi.ts` for `/backtest/*` per `specs/004-backtesting-core/contracts/backtest-api.md`
- [ ] T016 [P] Add unit tests for history limits / oversized reject in `backend/tests/unit/test_backtest_limits.py`
- [ ] T017 [P] Add unit tests for FIFO 20 completed + FIFO 5 failed retention in `backend/tests/unit/test_backtest_retention.py`

**Checkpoint**: Foundation ready — ranged market data, caps, DB/retention, historical fill adapter, validation skeleton, typed client; no XT types in `backtest/` package

---

## Phase 3: User Story 1 - Configure and run one historical backtest (Priority: P1) 🎯 MVP

**Goal**: Operator configures a bounded Dual EMA backtest (pair, timeframe, window, capital nesting, fee/slippage; optional max trades / profit / loss), runs it synchronously without credentials/real orders, and receives starting/ending capital, net P&L, and return %.

**Independent Test**: Valid config → completed summary with consistent capital/P&L/return %; invalid nesting, bad window, unsupported TF, or oversized history blocked with clear reason; no real-money controls on the path.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US1] Contract tests for `POST /backtest/runs` validation (`invalid_config`, `oversized_history`, `backtest_already_running`) and success summary fields in `backend/tests/contract/test_backtest_api.py`
- [ ] T019 [P] [US1] Frontend tests for backtest config validation (nesting, end > start, optional fields) in `frontend/src/__tests__/backtestConfig.test.tsx`

### Implementation for User Story 1

- [ ] T020 [US1] Implement chronological engine stub that loads closed candles via Feature 002 service, walks them once, applies shared Dual EMA + control + risk + HistoricalExecutionAdapter, end-of-run flatten, and builds minimal summary in `backend/app/backtest/engine.py`
- [ ] T021 [US1] Complete `service.py` sync run orchestration: one in-flight lock, validate → estimate/fetch → reject insufficient/oversized → run engine → persist completed/failed → return run in `backend/app/backtest/service.py`
- [ ] T022 [US1] Implement `POST /backtest/runs` and `GET /backtest/runs/{id}` in `backend/app/api/backtest.py`; mount router in `backend/app/main.py`
- [ ] T023 [P] [US1] Implement `BacktestConfigForm.tsx` (pair, TF, start/end, capital nesting, optional max trades / profit / loss rates with derived amounts, fee/slippage) in `frontend/src/features/backtest/BacktestConfigForm.tsx`
- [ ] T024 [P] [US1] Implement `BacktestResultsPanel.tsx` showing starting/ending capital, net P&L, return % in `frontend/src/features/backtest/BacktestResultsPanel.tsx`
- [ ] T025 [US1] Implement `useBacktest.ts` create/run + load-by-id hooks in `frontend/src/features/backtest/useBacktest.ts`
- [ ] T026 [US1] Add Backtest section (distinct from Simulation) on `frontend/src/pages/AutoTradingPage.tsx` with configure → run → summary; ensure real-money remains unavailable
- [ ] T027 [US1] Run T018–T019 tests and fix until passing; smoke quickstart scenario 1 against `specs/004-backtesting-core/quickstart.md`

**Checkpoint**: MVP — one historical backtest can be configured and completed with capital summary under Auto Trading

---

## Phase 4: User Story 2 - Same controlled pipeline over history (Priority: P1)

**Goal**: Closed-candle Dual EMA → Controller → Risk → HistoricalExecutionAdapter only; HOLD no balance change; next-open fills; missing N+1 → `approved_unexecutable` (not `rejected`); duplicate candle prevention; determinism; no live simulation state mutation.

**Independent Test**: Fixture series yields HOLD (no fill) and at least one approved fill or explicit rejection/unexecutable path that never bypasses control/risk; identical inputs → identical trades/summary.

### Tests for User Story 2

- [ ] T028 [P] [US2] Unit tests for next-open fills, end-close flatten, and missing N+1 → `approved_unexecutable`/`no_next_candle` (not `rejected`) in `backend/tests/unit/test_backtest_fills.py`
- [ ] T029 [P] [US2] Unit tests for duplicate-candle skip and chronological single-pass in `backend/tests/unit/test_backtest_duplicate_candle.py`
- [ ] T030 [P] [US2] Integration test: fixture candles through shared Dual EMA + control + risk + HistoricalExecutionAdapter in `backend/tests/integration/test_backtest_pipeline.py`
- [ ] T031 [P] [US2] Unit test determinism: identical config + fixture candles → identical decimal strings and trade lists in `backend/tests/unit/test_backtest_determinism.py`

### Implementation for User Story 2

- [ ] T032 [US2] Wire engine to **import** shared `dual_ema`, controller, risk, accounting, sizing, money (no Dual EMA fork) in `backend/app/backtest/engine.py`
- [ ] T033 [US2] Persist decision rows for every processed closed candle (`hold` / `approved` / `approved_unexecutable` / `rejected` / `forced`) via repository in `backend/app/backtest/engine.py` + `backend/app/backtest/repository.py`
- [ ] T034 [US2] Persist trade rows for strategy fills and end-of-run/early-exit flatten (`is_end_of_run_flatten` / forced flags) in `backend/app/backtest/execution.py` + repository
- [ ] T035 [US2] Enforce optional `max_trades` on strategy fills only; allow end-of-run flatten after cap in `backend/app/backtest/engine.py` (reuse Feature 003 risk semantics)
- [ ] T036 [US2] Enforce optional profit/loss early exits using liquidation Session NET (Feature 003 semantics) then flatten and stop further strategy entries in `backend/app/backtest/engine.py`
- [ ] T037 [US2] Ensure `backtest/` imports only normalized `market_data` models/service — never XT adapter types — across engine/service
- [ ] T038 [US2] Ensure backtest run uses ephemeral in-memory state and does not read/write Feature 003 simulation session tables/worker in `backend/app/backtest/service.py`
- [ ] T039 [US2] Run T028–T031 tests under `backend/tests/unit/` and `backend/tests/integration/` and fix until passing

**Checkpoint**: Historical pipeline matches Feature 003 authority with next-open historical fills and correct decision outcomes

---

## Phase 5: User Story 3 - Inspect trades and performance metrics (Priority: P1)

**Goal**: Completed runs expose full summary (including warm-up-independent B&H and per-candle equity max drawdown), trade list, decision history; persist across restart; list/delete; FIFO eviction.

**Independent Test**: After a run with ≥0 fills, summary fields present and consistent; trades/decisions inspectable; restart keeps completed runs ≤20; delete removes run; overflow drops oldest completed; failed overflow drops oldest failed (≤5).

### Tests for User Story 3

- [ ] T040 [P] [US3] Unit tests for max drawdown from per-candle liquidation equity, round-trip win/loss, and B&H independent of EMA warm-up in `backend/tests/unit/test_backtest_metrics.py`
- [ ] T041 [P] [US3] Contract tests for `GET /backtest/runs`, `GET .../trades`, `GET .../decisions`, `DELETE .../{id}` and retention behavior in `backend/tests/contract/test_backtest_api.py`
- [ ] T042 [P] [US3] Frontend tests for results/trades/decisions/list rendering in `frontend/src/__tests__/backtestResults.test.tsx`

### Implementation for User Story 3

- [ ] T043 [US3] Implement metrics module (equity series after every closed candle, max drawdown abs/%, round-trips, best/worst, cost-aware B&H from first executable window candle) in `backend/app/backtest/metrics.py`
- [ ] T044 [US3] Attach full summary to completed runs in `backend/app/backtest/engine.py` / `service.py` per data-model FR-016 fields
- [ ] T045 [US3] Implement list/get trades/decisions/delete routes in `backend/app/api/backtest.py` per `specs/004-backtesting-core/contracts/backtest-api.md`
- [ ] T046 [P] [US3] Implement `BacktestRunList.tsx` in `frontend/src/features/backtest/BacktestRunList.tsx`
- [ ] T047 [P] [US3] Implement `BacktestTrades.tsx` and `BacktestDecisions.tsx` in `frontend/src/features/backtest/`
- [ ] T048 [US3] Wire list → inspect summary/trades/decisions → delete into `useBacktest.ts` and Auto Trading backtest section
- [ ] T049 [US3] Run T040–T042 and T017 under `backend/tests/` / `frontend/src/__tests__/` and fix until passing; verify restart persistence per `specs/004-backtesting-core/quickstart.md`

**Checkpoint**: Inspectable journals and metrics; durable history with deterministic retention

---

## Phase 6: User Story 4 - Backtesting under Auto Trading UX (Priority: P2)

**Goal**: Reach backtesting from Auto Trading without a fourth primary nav; distinguish historical backtest from live simulation; primary configure/run/inspect usable at ~375px.

**Independent Test**: At ~375px and desktop, complete configure → run → summary/trades without desktop-only gestures; nav remains Dashboard / Auto Trading / Portfolio only.

### Tests for User Story 4

- [ ] T050 [P] [US4] Frontend tests for Auto Trading hosting both simulation and backtest sections with distinct labeling in `frontend/src/__tests__/backtestAutoTrading.test.tsx`

### Implementation for User Story 4

- [ ] T051 [US4] Polish `AutoTradingPage.tsx` layout: clear Backtest vs Simulation headings; no new primary nav item in app shell/router
- [ ] T052 [US4] Ensure primary backtest controls and summary/trade entry points are usable at ~375px (stacking, touch targets) across `frontend/src/features/backtest/*.tsx`
- [ ] T053 [US4] Add short non-misleading historical-evaluation copy (no guaranteed profit) in `frontend/src/features/backtest/BacktestResultsPanel.tsx`
- [ ] T054 [US4] Run T050 in `frontend/src/__tests__/backtestAutoTrading.test.tsx` and fix until passing

**Checkpoint**: Backtest reachable and usable under Auto Trading on phone-width

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, isolation proof, out-of-scope guardrails, quickstart validation

- [ ] T055 [P] Update root `README.md` with backtest overview, `/backtest` proxy, `MAX_BACKTEST_CANDLES=5000`, and link to `specs/004-backtesting-core/quickstart.md`
- [ ] T056 [P] Confirm Feature 002 candle contract/docs note optional start/end if public market API surface changes (update `specs/002-*/contracts/` or market API docs only if endpoints were extended publicly)
- [ ] T057 Add integration assertion that running backtest does not mutate an active simulation session in `backend/tests/integration/test_backtest_isolation.py`
- [ ] T058 [P] Grep/guard: no XT types or private trading APIs under `backend/app/backtest/`; no WebSocket progress channels for backtest
- [ ] T059 Run full validation scenarios in `specs/004-backtesting-core/quickstart.md` (manual or scripted smoke); fix gaps in `backend/app/backtest/` / `frontend/src/features/backtest/`
- [ ] T060 Propose git commit message for Feature 004 implementation in chat (do not auto-commit unless asked); reference `specs/004-backtesting-core/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on Foundational; builds on US1 engine/API (deepens pipeline correctness)
- **US3 (Phase 5)**: Depends on US1 run persistence; metrics/list/delete after engine produces journals (US2 decisions/trades recommended first)
- **US4 (Phase 6)**: Depends on US1 UI presence; polish after US3 inspect surfaces preferred
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2–US4
- **US2 (P1)**: After Foundational; extends US1 engine (same feature area)
- **US3 (P1)**: After US1 persistence path; preferably after US2 journals exist
- **US4 (P2)**: After US1 Auto Trading section exists; preferably after US3 list/inspect UI

### Within Each User Story

- Tests (where listed) SHOULD be written and fail before implementation
- Validation/limits before engine; engine before full metrics; API before UI wiring
- Story checkpoint before moving to next priority when sequencing solo

### Parallel Opportunities

- Phase 1: T002, T003, T005 in parallel after T001
- Phase 2: T006∥T009∥T013; T016∥T017 after limits/repository exist
- US1: T018∥T019; T023∥T024 after API client
- US2: T028∥T029∥T030∥T031 test authors in parallel
- US3: T040∥T041∥T042; T046∥T047
- US4: T050 can draft while T051–T053 proceed carefully on shared page
- Polish: T055∥T056∥T058

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract tests for POST /backtest/runs in backend/tests/contract/test_backtest_api.py"
Task: "Frontend config validation in frontend/src/__tests__/backtestConfig.test.tsx"

# UI pieces in parallel after client exists:
Task: "BacktestConfigForm.tsx"
Task: "BacktestResultsPanel.tsx"
```

---

## Parallel Example: User Story 3

```bash
Task: "Unit metrics tests in backend/tests/unit/test_backtest_metrics.py"
Task: "Contract list/trades/decisions/delete in backend/tests/contract/test_backtest_api.py"
Task: "Frontend results tests in frontend/src/__tests__/backtestResults.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Configure → run → capital summary under Auto Trading
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → MVP runnable backtest
3. US2 → pipeline/fill/decision correctness + determinism
4. US3 → full metrics, journals, retention, inspect/delete
5. US4 → phone-width UX polish
6. Polish → docs + isolation + quickstart

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Foundational:
   - Dev A: US1 API + engine stub
   - Dev B: US1 frontend form/results (against contract mocks)
   - Then US2 backend pipeline; US3 metrics/UI; US4 polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling work
- [Story] label maps task to US1–US4 for traceability
- Do not fork Dual EMA; do not reuse live simulation execution for historical timing
- Exact caps: 5000 candles; 20 completed; 5 failed
- Propose commits only; do not auto-commit unless asked
- Avoid: vague tasks, XT leakage into `backtest/`, fourth primary nav, WebSockets, optimization/grid search
