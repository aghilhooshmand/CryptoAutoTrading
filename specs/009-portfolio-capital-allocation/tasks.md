# Tasks: Portfolio & Capital Allocation Core

**Input**: Design documents from `/specs/009-portfolio-capital-allocation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context, constitution XXVIII, and quickstart require portfolio unit/contract tests plus frontend Portfolio coverage; Simulation/Backtest regression must stay green.

**Organization**: Tasks grouped by user story. Existing cash/allocation code is the foundation to **extend** (USDT holding = quote cash), not a rewrite.

**Spec precedence** (Session 2026-08-14, including holdings reconcile):
- One book: holdings + quote-cash reservation; USDT quantity **is** cash
- `available = quote_cash − reserved`; `reserved ≤ quote_cash`
- Operator local/manual non-quote holdings (quantity; optional average cost); provenance `local_manual`
- Value via Feature 002 public `{asset}_usdt` quotes; never invent prices
- Stale last-known included with stale indicator; missing price excluded from equity; `equityComplete` false when any holding unvalued
- Snapshots on meaningful book mutations only; no GET snapshots; 009 UI current-state (no charts)
- Deployed = `0`; positions = `[]` in 009
- Allocations reserve USDT only; no trading side effects; no XT private
- Package: `backend/app/portfolio/`
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4 / US5
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/009-portfolio-capital-allocation/`, `docs/ROADMAP.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing 009 reservation package and Feature 002 quote access

- [X] T001 Verify existing portfolio paths (`backend/app/portfolio/`, `backend/app/api/portfolio.py`, `frontend/src/pages/PortfolioPage.tsx`, `frontend/src/features/portfolio/`, `frontend/src/services/portfolioApi.ts`, `frontend/vite.config.ts`) per plan.md — extend, do not replace
- [X] T002 [P] Confirm Feature 002 `MarketDataService.get_quote` in `backend/app/market_data/service.py` can be reused for `{asset}_usdt` valuation (public only; no XT private) per research Decision 4

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Holdings table, cash→USDT migration, valuation, snapshot persistence, read model — blocks all stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T003 Add `PortfolioHoldingRow` and `PortfolioSnapshotRow` in `backend/app/db/models.py`; ensure `init_db` / light migration in `backend/app/db/session.py` and `backend/app/portfolio/repository.py` copies existing `portfolio.cash` into a `usdt` holding once per `data-model.md`
- [X] T004 [P] Extend capital identity in `backend/app/portfolio/identity.py`: `quote_cash` from USDT quantity; `available = quote_cash − reserved`; helpers for summing valued `marketValue` and `equityComplete` per FR-003 / FR-001d
- [X] T005 Implement holdings CRUD + snapshot append (same transaction as book mutation) in `backend/app/portfolio/repository.py` per `data-model.md` / research Decisions 1, 5
- [X] T006 [P] Implement public-quote valuation in `backend/app/portfolio/valuation.py` (USDT 1:1 fresh; other assets via `get_quote`; 60s stale; never invent; unvalued excluded) per research Decision 4 / FR-011a
- [X] T007 Extend snapshot assembly in `backend/app/portfolio/service.py` so GET returns holdings, `cash` from USDT, `equity` / `equityComplete` / `unvaluedAssets`, deployed `"0"`, positions `[]`; **GET must not** insert `portfolio_snapshots` per contracts/portfolio-api.md
- [X] T008 Point funding and allocation mutations in `backend/app/portfolio/service.py` and `backend/app/api/portfolio.py` at USDT holding as quote cash (async handlers if awaiting quotes); keep reservation invariants; do not call simulation/backtest start
- [X] T009 [P] Unit tests: cash→USDT migration, identity, partial/stale valuation, corrupt fail-closed, GET does not snapshot, in `backend/tests/unit/test_portfolio_service.py` and/or `backend/tests/unit/test_portfolio_valuation.py`
- [X] T010 [P] Contract tests: unfunded GET `cash` `"0"`; funding still sets cash via USDT holding; `equityComplete` present, in `backend/tests/contract/test_portfolio_api.py` per contracts/portfolio-api.md
- [X] T011 Run baseline regression: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q` must pass

**Checkpoint**: One-book read path + migration ready; stories can add holdings writes and UI

---

## Phase 3: User Story 1 - Inspect exchange-style holdings and portfolio value (Priority: P1) 🎯 MVP

**Goal**: Operator funds USDT, records local/manual holdings, and inspects quantity, price, value, weight, cost basis/P&L when known, equity (partial if needed), provenance.

**Independent Test**: Fund `1000` USDT; record BTC `0.005` with optional average cost; open Portfolio — holdings and totals reconcile; local/manual not labeled as live XT.

### Tests for User Story 1

- [X] T012 [P] [US1] Contract tests in `backend/tests/contract/test_portfolio_api.py`: `PUT /portfolio/funding`; `PUT /portfolio/holdings` for `btc`; `DELETE /portfolio/holdings/btc`; `PUT` `usdt` via holdings returns `400`; snapshot invariants (`cash` = USDT qty; `equity` = sum of valued `marketValue`)
- [X] T013 [P] [US1] Frontend tests in `frontend/src/__tests__/portfolio.test.tsx`: holdings table (asset, quantity, USDT units, provenance local/manual); funding; ~375px fund/record actions; help for equity vs cash per FR-010–FR-011 / SC-001 / SC-006 / `docs/UI_UX_STANDARDS.md`

### Implementation for User Story 1

- [X] T014 [US1] Implement `PUT /portfolio/holdings` and `DELETE /portfolio/holdings/{asset}` in `backend/app/portfolio/service.py` and `backend/app/api/portfolio.py` per contracts/portfolio-api.md / FR-001c (reject `usdt` on holdings upsert)
- [X] T015 [P] [US1] Extend `frontend/src/services/portfolioApi.ts` with snapshot types (`holdings`, `equityComplete`, `unvaluedAssets`, provenance) plus `putHolding` / `deleteHolding`
- [X] T016 [US1] Add holdings inspect + record/adjust/remove UI in `frontend/src/features/portfolio/` wired from `frontend/src/pages/PortfolioPage.tsx` (confirm delete; busy/error; provenance visible)
- [X] T017 [US1] Ensure funding UI in `frontend/src/features/portfolio/PortfolioCapitalPanel.tsx` presents quote cash as the USDT holding and equity as sum of valued holdings (not `equity === cash` once another valued asset exists) per FR-001a / FR-001d
- [X] T018 [US1] Run T009–T013; fix until passing

**Checkpoint**: MVP — fund USDT, record a local holding, inspect valued book

---

## Phase 4: User Story 2 - Create and manage explicit capital allocations (Priority: P1)

**Goal**: Allocations still reserve **quote cash** after holdings exist; over-reserve rejected; BTC quantity unchanged by allocate.

**Independent Test**: Cash `1000`, BTC holding present; two allocations totaling ≤ available; overspend rejected; BTC qty unchanged.

### Tests for User Story 2

- [X] T019 [P] [US2] Contract tests in `backend/tests/contract/test_portfolio_api.py`: POST/PATCH/DELETE allocations using USDT cash; over-reserve `400` leaves holdings+prior allocations; shared `targetRef` allowed; `cash < reserved` funding reject still holds
- [X] T020 [P] [US2] Frontend tests in `frontend/src/__tests__/portfolio.test.tsx`: create/resize/release; overspend error; confirm release; busy; allocation does not imply strategy-owned wallets

### Implementation for User Story 2

- [X] T021 [US2] Verify/fix allocation create/resize/release in `backend/app/portfolio/service.py` against USDT holding quote cash per FR-002 / FR-003 / FR-006
- [X] T022 [US2] Keep allocation UI in `frontend/src/features/portfolio/AllocationPanel.tsx` working with the expanded snapshot; reserved USDT must not alter non-quote holding quantities
- [X] T023 [US2] Run T019–T020; fix until passing

**Checkpoint**: SC-002 — safe allocations under quote-cash identity with holdings present

---

## Phase 5: User Story 3 - Inspect allocation-level accounting (Priority: P2)

**Goal**: Each allocation shows reserved size; portfolio holdings/equity remain the single book (no double-count).

**Independent Test**: Two allocations; inspect each; equity still equals valued holdings, not holdings + reserved.

### Tests for User Story 3

- [X] T024 [P] [US3] Frontend test in `frontend/src/__tests__/portfolio.test.tsx`: allocation cards show id/label/reservedSize and parent available; `allocationsDoNotAffectEquity` (or equivalent) still true when holdings exist

### Implementation for User Story 3

- [X] T025 [US3] Keep allocation detail/summary in `frontend/src/features/portfolio/AllocationPanel.tsx` (reserved mandatory; no-activity P&L placeholders; not a second portfolio) per FR-005
- [X] T026 [US3] Run T024; fix until passing

**Checkpoint**: Allocation inspection within one holdings book

---

## Phase 6: User Story 4 - Persist portfolio, holdings, and allocations (Priority: P1)

**Goal**: Reload restores quantities and reservations; rejected mutations never persist; book mutations append historical snapshots (GET does not).

**Independent Test**: Fund + record holding + allocate; reload same quantities/reservations; failed over-reserve then GET unchanged.

### Tests for User Story 4

- [X] T027 [P] [US4] Contract/persistence tests in `backend/tests/contract/test_portfolio_api.py`: fund + holding + allocation; new GET same cash/holdings/allocations; failed over-reserve then GET unchanged per FR-007 / FR-008 / SC-003
- [X] T028 [P] [US4] Unit tests in `backend/tests/unit/test_portfolio_service.py`: successful funding/holding/allocation inserts one `portfolio_snapshots` row; GET does not per FR-007a / research Decision 5

### Implementation for User Story 4

- [X] T029 [US4] Persist snapshots in the same transaction as mutations in `backend/app/portfolio/repository.py` / `backend/app/portfolio/service.py` (reasons: funding, holding_upsert/delete, allocation_*) per `data-model.md`
- [X] T030 [US4] Keep fail-closed `warning` display in `frontend/src/pages/PortfolioPage.tsx` / `frontend/src/features/portfolio/`; quantities must survive reload
- [X] T031 [US4] Run T027–T028; fix until passing

**Checkpoint**: SC-003 — persistence + leave-last-good + snapshot-on-mutation

---

## Phase 7: User Story 5 - Current-state analytics (Priority: P2)

**Goal**: Totals, weights, P&L/return only when data exists; partial/stale labeled; no history charts.

**Independent Test**: Valued BTC+USDT show weights; missing price → unvalued + partial equity label; no drawdown/value-over-time UI.

### Tests for User Story 5

- [X] T032 [P] [US5] Unit/contract tests in `backend/tests/unit/test_portfolio_valuation.py` and/or `backend/tests/contract/test_portfolio_api.py`: missing quote → excluded from equity + `equityComplete` false; stale quote included with `priceStatus` stale; unknown cost → null unrealized/return per FR-011a / SC-008
- [X] T033 [P] [US5] Frontend tests in `frontend/src/__tests__/portfolio.test.tsx`: partial equity labeled; stale indicator; no value-over-time or drawdown controls per SC-007 / SC-008 / FR-007a

### Implementation for User Story 5

- [X] T034 [US5] Surface `equityComplete`, `unvaluedAssets`, stale `priceStatus`, weights, and P&L-when-known in `frontend/src/features/portfolio/` (no snapshot-list or charts) per FR-010 / FR-011a
- [X] T035 [US5] Run T032–T033; fix until passing

**Checkpoint**: Honest current-state analytics only

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Regression, docs, UX, safety

- [X] T036 [P] Re-run Simulation/Backtest contracts: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q` per FR-009 / SC-005
- [X] T037 [P] Frontend portfolio tests: `npm test -- --run src/__tests__/portfolio` from `frontend/`
- [X] T038 Execute quickstart automated checks in `specs/009-portfolio-capital-allocation/quickstart.md` and fix gaps
- [X] T039 [P] Review Portfolio UI against `docs/UI_UX_STANDARDS.md` (holdings vs cash units, provenance, partial equity, confirm destructive actions, 375px)
- [X] T040 Keep Feature 009 `IN PROGRESS` in `docs/ROADMAP.md` until a later completion audit; do not mark DONE in this task list
- [X] T041 Confirm no credentials/real-money/strategy mutation in `backend/app/portfolio/`, `backend/app/api/portfolio.py`, `frontend/src/features/portfolio/`
- [X] T042 Propose commit message for holdings-extension work (do not auto-commit unless asked)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies
- **Phase 2 (Foundational)** → after Setup; **blocks all stories**
- **Phase 3 (US1)** → after Foundational — MVP holdings + fund + inspect
- **Phase 4 (US2)** → after US1 (allocations against USDT cash with other holdings present)
- **Phase 5 (US3)** → after US2
- **Phase 6 (US4)** → after Foundational; strongest after US1/US2 mutations exist
- **Phase 7 (US5)** → after US1 valuation path
- **Phase 8 (Polish)** → after desired stories

### User Story Dependencies

```text
Foundational (USDT holding = cash, valuation, snapshots)
     │
     ▼
   US1 Holdings inspect + fund + record   ← MVP
     │
     ├──────────────────► US5 Current-state analytics
     ▼
   US2 Allocations ──────────► US3 Allocation inspect
     │
     └──────────────────────► US4 Persistence + snapshot-on-mutation
```

### Parallel Opportunities

- T002; T004/T006; T009/T010 after models exist
- Within US1: T012/T013/T015
- Within US2: T019/T020
- Within US4: T027/T028
- Within US5: T032/T033
- Polish T036/T037/T039

---

## Parallel Example: User Story 1

```text
# After T007–T008 sketched:
T012 Contract funding + holdings tests
T013 Frontend holdings UI tests
T015 portfolioApi types/clients
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2: Migration + valuation + GET holdings
2. Phase 3: Fund USDT, record BTC, inspect equity/weights
3. **STOP and VALIDATE**: Multi-asset book visible; cash identity still holds
4. Then US2 allocations immediately (core reservation payoff)

### Incremental Delivery

1. Foundation → USDT holding + valued GET
2. US1 → fund + local holdings UI
3. US2–US3 → allocations unchanged semantically
4. US4 → snapshots on mutation
5. US5 → partial/stale labels, no charts
6. Polish → quickstart + regression

### Suggested MVP scope

**US1 only** (fund USDT + record a local holding + inspect). US2 should follow in the same delivery so reservation still works on the one book.

---

## Notes

- [P] = different files, no incomplete dependencies
- [USn] maps to spec user stories 1–5
- Commit only when asked; keep portfolio free of trading authority
- Do not migrate Simulation/Backtest fill ledgers
- Do not add `GET /portfolio/snapshots` or history charts in 009
- Money/quantities remain decimal strings

---

## Task Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 42 |
| **US1** | 7 (T012–T018) |
| **US2** | 5 (T019–T023) |
| **US3** | 3 (T024–T026) |
| **US4** | 5 (T027–T031) |
| **US5** | 4 (T032–T035) |
| **Setup + Foundational + Polish** | 18 (T001–T011, T036–T042) |
| **Parallel opportunities** | Yes — marked [P] across phases |

**Format validation**: All tasks use `- [ ]`, Task IDs T001–T042, [P]/[USn] where required, and file paths in descriptions.

---

## Phase 9: Convergence

- [X] T043 Add derived portfolio total P&L (realized + unrealized when defined) and total return (when cost basis exists) to the GET snapshot in `backend/app/portfolio/service.py` and surface them on `frontend/src/features/portfolio/PortfolioCapitalPanel.tsx`; omit as unknown when not defined per FR-001d / US5/AC1 (partial)
