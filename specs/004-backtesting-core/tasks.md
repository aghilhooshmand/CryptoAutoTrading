# Tasks: Backtesting Core

**Input**: Design documents from `/specs/004-backtesting-core/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — Constitution XXVIII and plan Technical Context require trading-critical automated tests (fills, metrics, limits, determinism, contracts, pipeline). Spec success criteria SC-002–SC-006a are test-backed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Spec precedence**: Latest `spec.md` clarifications (Session 2026-08-11 + plan refinements + analyze remediations) override older wording where they differ:
- Shared strategy/controller/risk/accounting; **HistoricalExecutionAdapter** for fills (not live simulation execution)
- Buy-and-hold starts at first executable candle in the **requested window**, independent of EMA warm-up
- Synchronous execution under **5000**-candle cap (v1)
- FIFO **20** completed + FIFO **5** failed; `approved_unexecutable` ≠ `rejected`
- Constitution V **1.2.0** historical-backtest exception (optional profit/loss/max_trades; window replaces duration)
- Fewer than **21** closed candles → `insufficient_history`; ≥21 → HOLD through warm-up
- Pre-run validation / oversized → **no** run row; post-accept fetch/execution failure → durable `failed` row
- T020 = engine/orchestration skeleton only; T033 owns shared Dual EMA + Controller + Risk wiring
- Ranged candles = **service/adapter only** (no public `/market/candles` start/end in Feature 004)
- Runnable Dual EMA MVP = **US1 + US2** (not US1 alone); warm-up HOLD covered by T030

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

- [ ] T006 [P] Extend adapter protocol with optional `start_time`/`end_time` (UTC ms) in `backend/app/market_data/adapters/base.py` (**service/adapter only** — do not change public HTTP `/market/candles` contract in Feature 004)
- [ ] T007 Extend XT Spot adapter ranged kline fetch + pagination (XT `startTime`/`endTime` only inside adapter) in `backend/app/market_data/adapters/xt_spot.py`
- [ ] T008 Extend `MarketDataService.get_candles` to accept optional start/end and return normalized closed candles only in `backend/app/market_data/service.py` (internal callers such as backtest; **no** public HTTP query-param expansion in this feature)
- [ ] T009 [P] Implement `MAX_BACKTEST_CANDLES = 5000` estimate/reject helpers in `backend/app/backtest/limits.py`
- [ ] T010 [P] Add SQLAlchemy tables `backtest_runs`, `backtest_trades`, `backtest_decisions` in `backend/app/db/models.py` per `specs/004-backtesting-core/data-model.md`
- [ ] T011 Wire table create for backtest models in FastAPI lifespan / `backend/app/db/session.py` (reuse existing engine pattern; optional `BACKTEST_DB_PATH`)
- [ ] T012 Implement repository CRUD + deterministic FIFO retention (20 completed, 5 failed; cascade; tie-break by id) in `backend/app/backtest/repository.py`
- [ ] T013 [P] Implement HistoricalExecutionAdapter next-open / end-close fill math (fee + adverse slippage; shared `money`/`accounting`/`position_sizing`) in `backend/app/backtest/execution.py` — do **not** import live `simulation.execution.simulation` for fill timing
- [ ] T014 Implement config validation skeleton (capital nesting, window, timeframe, optional max_trades/profit/loss, defaults fee/slippage, oversized reject before fetch) in `backend/app/backtest/service.py`
- [ ] T015 [P] Create typed frontend client `frontend/src/services/backtestApi.ts` for `/backtest/*` per `specs/004-backtesting-core/contracts/backtest-api.md`
- [ ] T016 [P] Add unit tests for history limits: oversized reject (no run row) **and** failing-first `insufficient_history` for empty series and fewer than 21 closed candles (zero fabricated fills) in `backend/tests/unit/test_backtest_limits.py`
- [ ] T017 [P] Add unit tests for FIFO 20 completed + FIFO 5 failed retention (including post-accept failed persistence) in `backend/tests/unit/test_backtest_retention.py`

**Checkpoint**: Foundation ready — ranged market data, caps, DB/retention, historical fill adapter, validation skeleton, typed client; no XT types in `backtest/` package

---

## Phase 3: User Story 1 - Configure and run one historical backtest (Priority: P1) 🎯 MVP (with US2)

**Goal**: Operator configures a bounded Dual EMA backtest (pair, timeframe, window, capital nesting, fee/slippage; optional max trades / profit / loss), runs it synchronously without credentials/real orders, and receives starting/ending capital, net P&L, and return %.

**Independent Test**: Valid config → completed summary with consistent capital/P&L/return %; invalid nesting, bad window, unsupported TF, or oversized history blocked with clear reason; no real-money controls on the path.

**Note**: Full Dual EMA/Controller/Risk behavior lands in US2 (T033). US1 delivers API/UI and engine skeleton; **demo-ready Dual EMA MVP = US1+US2**.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US1] Contract tests for `POST /backtest/runs`: `invalid_config`, `oversized_history` (no durable row), `backtest_already_running`, success summary fields, and post-accept `insufficient_history` for empty / fewer-than-21 series (durable `failed` row, zero fabricated fills) in `backend/tests/contract/test_backtest_api.py`
- [ ] T019 [P] [US1] Frontend tests for backtest config validation (nesting, end > start, optional fields) in `frontend/src/__tests__/backtestConfig.test.tsx`

### Implementation for User Story 1

- [ ] T020 [US1] Implement chronological **engine skeleton** in `backend/app/backtest/engine.py`: load closed candles via Feature 002 service, single-pass walk hooks, call-sites/stubs for strategy→control→risk→HistoricalExecutionAdapter, end-of-run flatten hook, and **minimal** capital summary placeholders — do **not** complete shared Dual EMA/Controller/Risk wiring here (owned by T033)
- [ ] T021 [US1] Complete `service.py` sync run orchestration in `backend/app/backtest/service.py`: one in-flight lock; pre-accept validate/estimate (`invalid_config`/`oversized_history` → **no** row); accept → `running` row; fetch/execute; empty or fewer-than-21 → persist `failed`/`insufficient_history`; other post-accept failures → persist `failed`; success → `completed`
- [ ] T022 [US1] Implement `POST /backtest/runs` and `GET /backtest/runs/{id}` in `backend/app/api/backtest.py`; mount router in `backend/app/main.py`
- [ ] T023 [P] [US1] Implement `BacktestConfigForm.tsx` (pair, TF, start/end, capital nesting, optional max trades / profit / loss rates with derived amounts, fee/slippage) in `frontend/src/features/backtest/BacktestConfigForm.tsx`
- [ ] T024 [P] [US1] Implement `BacktestResultsPanel.tsx` showing starting/ending capital, net P&L, return % in `frontend/src/features/backtest/BacktestResultsPanel.tsx`
- [ ] T025 [US1] Implement `useBacktest.ts` create/run + load-by-id hooks in `frontend/src/features/backtest/useBacktest.ts`
- [ ] T026 [US1] Add Backtest section (distinct from Simulation) on `frontend/src/pages/AutoTradingPage.tsx` with configure → run → summary; ensure real-money remains unavailable
- [ ] T027 [US1] Run T018–T019 tests and fix until passing; smoke quickstart scenario 1 against `specs/004-backtesting-core/quickstart.md`

**Checkpoint**: US1 configure/run/summary UI + API orchestration exist; Dual EMA/Controller/Risk path is still stubbed until T033 — treat **runnable Dual EMA MVP** as US1+US2 (see Implementation Strategy)

---

## Phase 4: User Story 2 - Same controlled pipeline over history (Priority: P1)

**Goal**: Closed-candle Dual EMA → Controller → Risk → HistoricalExecutionAdapter only; HOLD no balance change; next-open fills; missing N+1 → `approved_unexecutable` (not `rejected`); duplicate candle prevention; determinism; no live simulation state mutation.

**Independent Test**: Fixture series yields HOLD (no fill) and at least one approved fill or explicit rejection/unexecutable path that never bypasses control/risk; identical inputs → identical trades/summary.

### Tests for User Story 2

- [ ] T028 [P] [US2] Unit tests for next-open fills, end-close flatten, and missing N+1 → `approved_unexecutable`/`no_next_candle` (not `rejected`) in `backend/tests/unit/test_backtest_fills.py`
- [ ] T029 [P] [US2] Unit tests for duplicate-candle skip and chronological single-pass in `backend/tests/unit/test_backtest_duplicate_candle.py`
- [ ] T030 [P] [US2] Unit tests for Dual EMA warm-up HOLD on ≥21 closed-candle windows (early HOLDs, zero strategy fills until ready; FR-008b) in `backend/tests/unit/test_backtest_warmup.py`
- [ ] T031 [P] [US2] Integration test: fixture candles through shared Dual EMA + control + risk + HistoricalExecutionAdapter in `backend/tests/integration/test_backtest_pipeline.py`
- [ ] T032 [P] [US2] Unit test determinism: identical config + fixture candles → identical decimal strings and trade lists in `backend/tests/unit/test_backtest_determinism.py`

### Implementation for User Story 2

- [ ] T033 [US2] **Complete and harden** shared Dual EMA + Controller + Risk wiring in `backend/app/backtest/engine.py` (import Feature 003 modules; no Dual EMA fork); replace T020 stubs so non-HOLD paths always pass control/risk before HistoricalExecutionAdapter; warm-up HOLD on ≥21-candle windows until ready
- [ ] T034 [US2] Persist decision rows for every processed closed candle (`hold` / `approved` / `approved_unexecutable` / `rejected` / `forced`) via repository in `backend/app/backtest/engine.py` + `backend/app/backtest/repository.py`
- [ ] T035 [US2] Persist trade rows for strategy fills and end-of-run/early-exit flatten (`is_end_of_run_flatten` / forced flags) in `backend/app/backtest/execution.py` + repository
- [ ] T036 [US2] Enforce optional `max_trades` on strategy fills only; allow end-of-run flatten after cap in `backend/app/backtest/engine.py` (reuse Feature 003 risk semantics)
- [ ] T037 [US2] Enforce optional profit/loss early exits using liquidation Session NET (Feature 003 semantics) then flatten and stop further strategy entries in `backend/app/backtest/engine.py`
- [ ] T038 [US2] Ensure `backtest/` imports only normalized `market_data` models/service — never XT adapter types — across engine/service
- [ ] T039 [US2] Ensure backtest run uses ephemeral in-memory state and does not read/write Feature 003 simulation session tables/worker in `backend/app/backtest/service.py`
- [ ] T040 [US2] Run T028–T032 tests under `backend/tests/unit/` and `backend/tests/integration/` and fix until passing

**Checkpoint**: Historical pipeline matches Feature 003 authority with next-open historical fills and correct decision outcomes — **runnable Dual EMA MVP** (US1+US2)

---

## Phase 5: User Story 3 - Inspect trades and performance metrics (Priority: P1)

**Goal**: Completed runs expose full summary (including warm-up-independent B&H and per-candle equity max drawdown), trade list, decision history; persist across restart; list/delete; FIFO eviction.

**Independent Test**: After a run with ≥0 fills, summary fields present and consistent; trades/decisions inspectable; restart keeps completed runs ≤20; delete removes run; overflow drops oldest completed; failed overflow drops oldest failed (≤5).

### Tests for User Story 3

- [ ] T041 [P] [US3] Unit tests for max drawdown from per-candle liquidation equity, round-trip win/loss, and B&H independent of EMA warm-up in `backend/tests/unit/test_backtest_metrics.py`
- [ ] T042 [P] [US3] Contract tests for `GET /backtest/runs`, `GET .../trades`, `GET .../decisions`, `DELETE .../{id}` and retention behavior in `backend/tests/contract/test_backtest_api.py`
- [ ] T043 [P] [US3] Frontend tests for results/trades/decisions/list rendering in `frontend/src/__tests__/backtestResults.test.tsx`

### Implementation for User Story 3

- [ ] T044 [US3] Implement metrics module (equity series after every closed candle, max drawdown abs/%, round-trips, best/worst, cost-aware B&H from first executable window candle) in `backend/app/backtest/metrics.py`
- [ ] T045 [US3] Attach full summary to completed runs in `backend/app/backtest/engine.py` / `service.py` per data-model FR-016 fields
- [ ] T046 [US3] Implement list/get trades/decisions/delete routes in `backend/app/api/backtest.py` per `specs/004-backtesting-core/contracts/backtest-api.md`
- [ ] T047 [P] [US3] Implement `BacktestRunList.tsx` in `frontend/src/features/backtest/BacktestRunList.tsx`
- [ ] T048 [P] [US3] Implement `BacktestTrades.tsx` and `BacktestDecisions.tsx` in `frontend/src/features/backtest/`
- [ ] T049 [US3] Wire list → inspect summary/trades/decisions → delete into `useBacktest.ts` and Auto Trading backtest section
- [ ] T050 [US3] Run T041–T043 and T017 under `backend/tests/` / `frontend/src/__tests__/` and fix until passing; verify restart persistence per `specs/004-backtesting-core/quickstart.md`

**Checkpoint**: Inspectable journals and metrics; durable history with deterministic retention

---

## Phase 6: User Story 4 - Backtesting under Auto Trading UX (Priority: P2)

**Goal**: Reach backtesting from Auto Trading without a fourth primary nav; distinguish historical backtest from live simulation; primary configure/run/inspect usable at ~375px.

**Independent Test**: At ~375px and desktop, complete configure → run → summary/trades without desktop-only gestures; nav remains Dashboard / Auto Trading / Portfolio only.

### Tests for User Story 4

- [ ] T051 [P] [US4] Frontend tests for Auto Trading hosting both simulation and backtest sections with distinct labeling in `frontend/src/__tests__/backtestAutoTrading.test.tsx`

### Implementation for User Story 4

- [ ] T052 [US4] Polish `AutoTradingPage.tsx` layout: clear Backtest vs Simulation headings; no new primary nav item in app shell/router
- [ ] T053 [US4] Ensure primary backtest controls and summary/trade entry points are usable at ~375px (stacking, touch targets) across `frontend/src/features/backtest/*.tsx`
- [ ] T054 [US4] Add short non-misleading historical-evaluation copy (no guaranteed profit) in `frontend/src/features/backtest/BacktestResultsPanel.tsx`
- [ ] T055 [US4] Run T050 in `frontend/src/__tests__/backtestAutoTrading.test.tsx` and fix until passing

**Checkpoint**: Backtest reachable and usable under Auto Trading on phone-width

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, isolation proof, out-of-scope guardrails, quickstart validation

- [ ] T056 [P] Update root `README.md` with backtest overview, `/backtest` proxy, `MAX_BACKTEST_CANDLES=5000`, and link to `specs/004-backtesting-core/quickstart.md`
- [ ] T057 [P] Do **not** expand public Feature 002 HTTP `/market/candles` for start/end in Feature 004 (service-only ranged fetch). Only update `specs/002-*/contracts/` if a future change explicitly adds public query params; otherwise leave 002 HTTP docs unchanged
- [ ] T058 Add integration assertion that running backtest does not mutate an active simulation session in `backend/tests/integration/test_backtest_isolation.py`
- [ ] T059 [P] Grep/guard: no XT types or private trading APIs under `backend/app/backtest/`; no WebSocket progress channels for backtest
- [ ] T060 Run full validation scenarios in `specs/004-backtesting-core/quickstart.md` (manual or scripted smoke); fix gaps in `backend/app/backtest/` / `frontend/src/features/backtest/`
- [ ] T061 Propose git commit message for Feature 004 implementation in chat (do not auto-commit unless asked); reference `specs/004-backtesting-core/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — configure/run API + UI; engine stubs OK
- **US2 (Phase 4)**: Depends on Foundational; completes Dual EMA/Controller/Risk wiring (T033) — **required for runnable Dual EMA MVP**
- **US3 (Phase 5)**: Depends on US1 persistence path; preferably after US2 journals exist
- **US4 (Phase 6)**: Depends on US1 Auto Trading section exists; preferably after US3 list/inspect UI
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (Phase 3)**: Depends on Foundational — configure/run API + UI; engine stubs OK
- **US2 (Phase 4)**: Completes Dual EMA/Controller/Risk wiring (T033) — **required for runnable Dual EMA MVP**
- **US3 (Phase 5)**: Depends on US1 persistence; preferably after US2 journals
- **US4 (Phase 6)**: Depends on US1 Auto Trading section; preferably after US3 inspect UI

### Within Each User Story

- Tests (where listed) SHOULD be written and fail before implementation
- Validation/limits before engine; engine before full metrics; API before UI wiring
- Story checkpoint before moving to next priority when sequencing solo

### Parallel Opportunities

- Phase 1: T002, T003, T005 in parallel after T001
- Phase 2: T006∥T009∥T013; T016∥T017 after limits/repository exist
- US1: T018∥T019; T023∥T024 after API client
- US2: T028∥T029∥T030∥T031∥T032 test authors in parallel
- US3: T041∥T042∥T043; T047∥T048
- US4: T051 can draft while T052–T054 proceed carefully on shared page
- Polish: T056∥T057∥T059

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

### MVP First (User Stories 1+2 — runnable Dual EMA)

US1 alone delivers configure/run/summary surfaces with an engine **skeleton**.
Shared Dual EMA + Controller + Risk wiring completes in US2 (T033). Treat the
**first demo-ready MVP** as Phases 1–4 through the US2 checkpoint (T040).

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (API/UI + skeleton)
4. Complete Phase 4: User Story 2 (pipeline wiring + fills + warm-up HOLD tests)
5. **STOP and VALIDATE**: Configure → run Dual EMA backtest → capital summary + decisions/fills under Auto Trading
6. Demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → configure/run API + UI (skeleton engine)
3. US2 → **runnable Dual EMA MVP** (pipeline/fill/decision correctness + determinism + warm-up HOLD)
4. US3 → full metrics, journals, retention, inspect/delete
5. US4 → phone-width UX polish
6. Polish → docs + isolation + quickstart

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Foundational:
   - Dev A: US1 API + engine skeleton, then US2 T033 wiring
   - Dev B: US1 frontend form/results (against contract mocks)
   - Then US2 tests (incl. T030 warm-up); US3 metrics/UI; US4 polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling work
- [Story] label maps task to US1–US4 for traceability
- Do not fork Dual EMA; do not reuse live simulation execution for historical timing
- Exact caps: 5000 candles; 20 completed; 5 failed; min 21 closed candles
- Ranged candles: **service/adapter only** in Feature 004 (no public `/market/candles` start/end)
- Runnable Dual EMA MVP = US1 + US2 (not US1 alone)
- Propose commits only; do not auto-commit unless asked
- Avoid: vague tasks, XT leakage into `backtest/`, fourth primary nav, WebSockets, optimization/grid search
