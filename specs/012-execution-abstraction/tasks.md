# Tasks: Execution Abstraction

**Input**: Design documents from `/specs/012-execution-abstraction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md, call-sites.md

**Tests**: Required — unit (`test_execution_economics.py`,
`test_real_execution_stub.py`) plus behavior-preserving regression gates from
plan.md / FR-017 / SC-001–SC-004 (Backtest fills/pipeline, Simulation
pipeline/forced-close, risk rejects, Portfolio fill-apply). No frontend Vitest
expected.

**Organization**: New `backend/app/execution/` package; thin Historical /
Simulation / Real adapters; compatibility shims at old import paths; mode
callers keep timing, journals, flatten, Portfolio apply. No HTTP/UI/schema.
Propose commits only; do not auto-commit. Keep Feature 012 `IN PROGRESS` on
`docs/ROADMAP.md` until completion workflow.

**Spec locks** (must hold through all tasks):
- No intentional 003 Simulation / 004 Backtest behavior change
- Historical next-open; Simulation live/safe mark; flatten orchestration mode-owned
- Shared fill economics + rejects only; journal/Portfolio stay mode-specific
- Production Historical + Simulation **strategy fills** call through `ExecutionEngine.execute` (wrappers may exist only if they call `execute`, never `economics` directly)
- Comparison historical fills = Backtest leg runner → `run_engine` → `HistoricalExecutionAdapter` (no third fill fork)
- Real = code/test stub only; `real_execution_unavailable`; no operator UI/API mode
- Backtest/Comparison MUST NOT gain Portfolio dependency
- Compatibility shims at old import paths MUST be **re-export-only** (no second fill implementation)
- No Feature 010 Risk / Decision Log Mode / History freeze semantic changes (FR-016)
- Runtime name remains `SimulationExecutionEngine` (constitution “SimulationExecutionAdapter” is conceptual)

**Analyze remediation** (2026-08-15): I1 shim re-export-only; I2 execute-not-helpers; I3 field-level dual-oracle tests; I8 call-site inventory in `call-sites.md` (not `__init__.py` comments).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US5 map to spec stories (US4 = Comparison / former 3b; US5 = Real)

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Docs: `specs/012-execution-abstraction/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

**Purpose**: Package skeleton and inventory of call sites

- [x] T001 Create `backend/app/execution/` package skeleton (`__init__.py` placeholder exports only — no call-site commentary) per `plan.md`
- [x] T002 [P] Keep call-site inventory current in `specs/012-execution-abstraction/call-sites.md` (Simulation pipeline/session_service, Backtest engine/execution, simulation execution shims, Comparison → leg runner → `run_engine`); do **not** put this inventory in `backend/app/execution/__init__.py`

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Shared port types + economics core used by all adapters

**⚠️ CRITICAL**: No user story adapter wiring until this phase completes

- [x] T003 Implement `ExecutionIntent`, `FillResult`, and `ExecutionEngine` Protocol in `backend/app/execution/port.py` per `data-model.md` and `contracts/execution-contract.md` (match existing Simulation `FillResult` field set: `ok`, `reason_code`, `reason_message`, `fill`, `qty`; same shape as today’s `HistoricalFillResult`)
- [x] T004 Implement shared buy/sell fill economics + stable reject codes (`invalid_side`, `conflicting_position_state`, `insufficient_balance`) in `backend/app/execution/economics.py` using `app.simulation.accounting` / `position_sizing` / `money` only — consume caller `intent.reference_price`; MUST NOT import candle/quote/market-data modules; MUST NOT select next-open vs live mark
- [x] T005 [P] Export public symbols from `backend/app/execution/__init__.py` (`ExecutionIntent`, `FillResult`, `ExecutionEngine`, adapters as needed) — exports only, no inventory comments
- [x] T006 [P] Add unit tests in `backend/tests/unit/test_execution_economics.py`: fixed intent matrix; assert shared economics (and later both adapters) match **current** `SimulationExecutionEngine` and `HistoricalExecutionAdapter` field-by-field for `qty`, `FillQuote.notional` / `fee` / `slippage_cost` / `cash_delta` / `fill_price` / `reference_price`, dust handling, BUY/SELL sizing, and `reason_code` — run this dual-oracle **before** deleting old fill bodies

**Checkpoint**: Shared contract + economics exist and dual-oracle unit-tested; adapters not yet production-wired

---

## Phase 3: User Story 1 - One execution contract for modes (Priority: P1) 🎯 MVP

**Goal**: Historical and Simulation strategy fills share one contract; economics consolidated; production paths call through adapters.

**Independent Test**: Both adapters implement `execute`; Simulation + Backtest regressions green with unchanged expectations; no parallel private fill math left in production strategy-fill paths.

### Tests

- [x] T007 [P] [US1] Extend `backend/tests/unit/test_execution_economics.py` (or add `backend/tests/unit/test_execution_adapters_contract.py`) asserting Historical and Simulation adapters both satisfy `ExecutionEngine.execute` for identical intents → identical `FillResult` economics/codes (field-level)

### Implementation

- [x] T008 [US1] Implement thin `SimulationExecutionEngine` in `backend/app/execution/simulation.py` whose `execute` delegates to `economics.py` only (no journal/Portfolio/Controller/Risk side effects inside adapter)
- [x] T009 [P] [US1] Implement thin `HistoricalExecutionAdapter` in `backend/app/execution/historical.py` with `execute` → `economics`; `buy`/`sell` wrappers MUST build `ExecutionIntent` and call **`self.execute` only** (never call `economics` directly)
- [x] T010 [US1] Replace `backend/app/simulation/execution/port.py` and `backend/app/simulation/execution/simulation.py` with **re-export-only** shims to `app.execution` (preserve import paths); **zero** local fill math / `_buy` / `_sell` / `intended_notional` bodies
- [x] T011 [US1] Convert `backend/app/backtest/execution.py` to **re-export-only** `HistoricalExecutionAdapter` (+ optional `HistoricalFillResult = FillResult` alias) from `app.execution.historical`; remove duplicated fill math; engine keeps using `.ok` / `.fill` / `.qty` / `.reason_*`
- [x] T012 [US1] Wire Simulation strategy fills in `backend/app/simulation/pipeline.py` through `SimulationExecutionEngine.execute` / `ExecutionIntent` — keep journal + Portfolio apply **after** fill in pipeline
- [x] T013 [US1] Wire Simulation forced-close fill invocation in `backend/app/simulation/session_service.py` through Simulation adapter **`execute`** — keep flatten orchestration and unsafe-mark handling mode-owned
- [x] T014 [US1] Ensure Backtest strategy fills in `backend/app/backtest/engine.py` go through `HistoricalExecutionAdapter` such that every strategy fill reaches **`ExecutionEngine.execute`** (direct `execute` or `buy`/`sell` that only wraps `execute`); keep next-open / flatten reference selection and journals in the engine; `_flatten` may keep using `sell` wrapper
- [x] T015 [US1] Run US1 gates until green: `backend/tests/unit/test_execution_economics.py`, `backend/tests/unit/test_backtest_fills.py`, `backend/tests/unit/test_accounting.py`, `backend/tests/unit/test_risk_rejects.py`, `backend/tests/integration/test_simulation_pipeline.py`, `backend/tests/integration/test_backtest_pipeline.py` — **no intentional expectation edits**

**Checkpoint**: MVP — one contract; production Historical + Simulation strategy fills call through it; regressions pass

---

## Phase 4: User Story 2 - Preserve Historical vs Simulation semantics (Priority: P1)

**Goal**: Next-open stays Historical-only; live/safe mark stays Simulation-only; missing next candle and unsafe flatten unchanged.

**Independent Test**: Backtest next-open + `approved_unexecutable`; Simulation mark path + forced-close/unsafe behavior unchanged.

### Tests

- [x] T016 [P] [US2] Confirm / extend coverage in `backend/tests/unit/test_backtest_fills.py` for next-open strategy fill and missing-next-candle `approved_unexecutable` (no invented fill)
- [x] T017 [P] [US2] Confirm / extend coverage in `backend/tests/unit/test_forced_close.py` and `backend/tests/integration/test_simulation_pipeline.py` for live/safe mark fills and unsafe/unflattened behavior

### Implementation

- [x] T018 [US2] Audit `backend/app/backtest/engine.py` so `reference_price` for strategy fills remains next candle open; adapters never fetch candles/quotes
- [x] T019 [US2] Audit `backend/app/simulation/pipeline.py` (and mark helpers it uses) so Simulation `reference_price` remains the established live/safe mark path — not next-open
- [x] T020 [US2] Verify flatten orchestration remains mode-owned in `backend/app/backtest/engine.py` (`_flatten`) and `backend/app/simulation/session_service.py` — do not merge flatten into shared economics unless a regression suite proves equivalence (default: do not merge)
- [x] T021 [US2] Re-run T016–T017 gates plus `backend/tests/unit/test_backtest_fills.py` / `backend/tests/unit/test_forced_close.py` until green with unchanged expectations

**Checkpoint**: Mode price policies and flatten semantics preserved

---

## Phase 5: User Story 3 - Keep Backtest free of Portfolio (Priority: P1)

**Goal**: Historical execution has no Portfolio dependency; Simulation Portfolio apply stays Simulation-only after successful fills.

**Independent Test**: Backtest with fills leaves Portfolio reserved/available/holdings unchanged; Simulation Portfolio fill-apply suites still pass.

### Tests

- [x] T022 [P] [US3] Add or extend a focused test (prefer `backend/tests/unit/test_execution_portfolio_isolation.py` or extend an existing backtest+portfolio fixture) asserting Backtest run with fills does not change Portfolio reserved/available/holdings
- [x] T023 [P] [US3] Re-run Simulation Portfolio fill-apply related coverage in `backend/tests/contract/test_portfolio_api.py` (paths using `apply_simulation_fill`) to ensure Simulation side effects still work and remain outside shared economics

### Implementation

- [x] T024 [US3] Ensure `backend/app/execution/historical.py` and `backend/app/backtest/engine.py` / `backend/app/backtest/execution.py` do not import or call Portfolio mutation APIs
- [x] T025 [US3] Ensure Portfolio apply remains only on Simulation success path in `backend/app/simulation/pipeline.py` (and any existing Portfolio helper modules) — not inside `backend/app/execution/economics.py`
- [x] T026 [US3] Run T022–T023 until green

**Checkpoint**: Portfolio isolation for Historical proven; Simulation apply intact

---

## Phase 6: User Story 4 - Comparison shares Historical fills (Priority: P2)

**Goal**: Comparison historical fills continue via Backtest `run_engine` → same Historical adapter; orchestration unchanged.

**Independent Test**: Comparison tests green; import/path review shows no third fill fork.

### Tests

- [x] T027 [P] [US4] Run Comparison regression suite: `backend/tests/unit/test_comparison_orchestrator.py`, `backend/tests/integration/test_comparison_shared_candles.py`, `backend/tests/contract/test_comparison_api.py`

### Implementation

- [x] T028 [US4] Verify Comparison in `backend/app/comparison/` reaches Historical fills only via Backtest leg runner (`run_leg_with_prefetched_candles` or equivalent) → `run_engine` → `HistoricalExecutionAdapter` (no direct fill math / no new execution adapter in `app/comparison/`)
- [x] T029 [US4] Confirm `run_engine` in `backend/app/backtest/engine.py` uses shared `HistoricalExecutionAdapter` from `app.execution` (via re-export shim or direct import)
- [x] T030 [US4] Keep Comparison→Historical path documented in `specs/012-execution-abstraction/call-sites.md` and `quickstart.md` scenario 4 — no Comparison UX/API changes

**Checkpoint**: No third Historical fill fork; Comparison orchestration untouched

---

## Phase 7: User Story 5 - Real execution stub only (Priority: P2)

**Goal**: Real adapter on the shared contract; structured `real_execution_unavailable`; code/tests only; no operator selection.

**Independent Test**: Unit test constructs Real, gets failure code, no state mutation; UI/API have no Real mode.

### Tests

- [x] T031 [P] [US5] Add `backend/tests/unit/test_real_execution_stub.py`: `execute` → `ok=false`, `reason_code=real_execution_unavailable`, null fill/qty; assert no Portfolio/ledger mutation (no apply helpers called / no side effects)

### Implementation

- [x] T032 [US5] Implement `RealExecutionAdapter` in `backend/app/execution/real.py` per `contracts/execution-contract.md`
- [x] T033 [P] [US5] Export Real adapter from `backend/app/execution/__init__.py`
- [x] T034 [US5] Negative check: no Real execution mode on Simulation/Backtest create APIs (`backend/app/api/simulation.py`, `backend/app/api/backtest.py`) or frontend create flows — do not add UI; assert absence in `test_real_execution_stub.py` docstring and/or a small API schema/contract assertion; checklist in `quickstart.md`
- [x] T035 [US5] Run T031 (and T034 checks) until green

**Checkpoint**: Real stub ready for 013+ attachment; fail-closed; not operator-selectable

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Full quickstart gate, docs status, cleanup

- [x] T036 Run full quickstart validation from `specs/012-execution-abstraction/quickstart.md` (economics + Real stub + Backtest/Simulation/Portfolio/Comparison gates listed there)
- [x] T037 [P] DONE gate for shims: `backend/app/simulation/execution/port.py`, `backend/app/simulation/execution/simulation.py`, and `backend/app/backtest/execution.py` contain **no** local fill implementations (`_buy`/`_sell`/`intended_notional`/`buy_fill` bodies) — re-exports only
- [x] T038 [P] Grep review under `backend/app/execution/`: no XT private / order placement; no Controller/Risk/journal-repo/Portfolio-mutation imports; no candle/quote fetch; no divergent second `FillResult` type required for Historical (alias OK)
- [x] T039 Update `docs/ROADMAP.md` Feature 012 status to `DONE` only after T036 green (leave `IN PROGRESS` until then)
- [x] T040 Mark `specs/012-execution-abstraction/spec.md` Status appropriately; confirm FR-016 (no Risk / Decision Log Mode / History freeze semantic edits) held; ensure tasks checkboxes reflect completion for implement handoff

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on US1 wiring (semantics audit of those call sites)
- **US3 (Phase 5)**: Depends on US1 Historical/Simulation adapters existing
- **US4 (Phase 6)**: Depends on US1 Historical adapter + Backtest engine wiring
- **US5 (Phase 7)**: Depends on Foundational port types; can start after Phase 2 in parallel with US2–US4 if staffed, but typically after US1
- **Polish (Phase 8)**: Depends on US1–US5 complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no other story dependency — **MVP**
- **US2 (P1)**: After US1 call-site wiring
- **US3 (P1)**: After US1 adapters; parallelizable with US2 after US1
- **US4 (P2)**: After US1 Historical path stable
- **US5 (P2)**: After Foundational; parallelizable with US2–US4 once `port.py` exists

### Parallel Opportunities

- T002 with other Setup notes once T001 done
- T005 || T006 after T003–T004
- T008 then T009 [P] in parallel once economics ready
- T016 || T017 (US2 tests)
- T022 || T023 (US3 tests)
- T031 || T033 (US5)
- US3 and US5 can proceed in parallel after US1/Foundational as noted

---

## Parallel Example: User Story 1

```bash
# After T003–T006:
Task: "Implement SimulationExecutionEngine in backend/app/execution/simulation.py"
Task: "Implement HistoricalExecutionAdapter in backend/app/execution/historical.py"  # [P] with Simulation adapter

# After adapters + shims:
# Wire call sites sequentially (same behavioral gate):
# pipeline.py → session_service.py → backtest/engine.py → regression suite
```

---

## Parallel Example: User Stories 3 & 5 (after US1 / port)

```bash
Task: "Portfolio isolation test in backend/tests/unit/test_execution_portfolio_isolation.py"
Task: "Real stub test in backend/tests/unit/test_real_execution_stub.py"
Task: "Implement RealExecutionAdapter in backend/app/execution/real.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (port + economics + tests)
3. Phase 3 US1 (adapters, shims, wire Simulation + Historical strategy fills)
4. **STOP and VALIDATE** US1 regression gates
5. Continue US2→US5 then Polish

### Incremental Delivery

1. Setup + Foundational → shared contract exists
2. US1 → production paths on contract (MVP)
3. US2 → prove mode semantics
4. US3 → prove Portfolio isolation
5. US4 → prove Comparison shares Historical
6. US5 → Real stub for 013+
7. Polish → quickstart + ROADMAP DONE

### Suggested commit style (manual; do not auto-commit)

```text
feat(012): add shared execution port and economics

refactor(012): thin Historical/Simulation adapters and wire call sites

test(012): Real stub real_execution_unavailable + portfolio isolation

docs(012): mark Execution Abstraction DONE
```

---

## Notes

- [P] = different files, no incomplete dependencies
- Do not rename existing Simulation/Backtest reject codes
- Do not add operator Real mode or XT private calls
- Do not merge flatten/journal/Portfolio into `economics.py` by default
- Call-site inventory lives in `specs/012-execution-abstraction/call-sites.md`, not package `__init__` comments
- Behavior gate failures → fix adapter/wiring; do not “fix” by editing golden expectations unless a pre-existing bug is explicitly scoped

---

## Phase 9: Convergence

**Purpose**: Close remaining gaps found by `/speckit-converge` against post-implement code and docs (2026-08-15).

- [x] T041 Update Phase B summary table in `docs/ROADMAP.md` so Feature 012 status is `DONE` (section body already `DONE`; table still `IN PROGRESS`) per T039 / plan polish (partial)
- [x] T042 Refresh `specs/012-execution-abstraction/call-sites.md` “Today” / status columns to match post-012 reality (re-export-only shims, shared `app.execution` adapters, wrappers→`execute`) per T002 / plan:call-sites (partial)
