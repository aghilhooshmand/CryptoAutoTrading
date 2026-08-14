# Tasks: Portfolio & Capital Allocation Core
     
**Input**: Design documents from `/specs/009-portfolio-capital-allocation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Technical Context, constitution XXVIII, and quickstart require portfolio unit/contract tests plus frontend Portfolio coverage; Simulation/Backtest regression must stay green.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Spec precedence** (Session 2026-08-14 clarifications + plan/research):
- SQLite singleton portfolio + allocation rows; API under `/portfolio` (not `localStorage`)
- Explicit Portfolio **funding** for cash (not Settings / Simulation mirror)
- Capital identity: `available = cash − reserved`; `reserved ≤ cash`; `available ≥ 0`
- Deployed = `0` and positions = `[]` in Feature 009 (still visible)
- Allocations = reservations only; optional non-unique `targetRef`
- Reject funding cuts that would make `cash < reserved`
- Strategies never mutate portfolio balances/positions
- No Simulation/Backtest ledger migration; no trading side effects
- Portfolio primary nav UI; inherit `docs/UI_UX_STANDARDS.md`
- Package path locked: `backend/app/portfolio/`
- Propose commits only; do not auto-commit unless asked

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/009-portfolio-capital-allocation/`, `docs/ROADMAP.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm touch points; create portfolio package/UI stubs

- [X] T001 Verify Portfolio route and related paths exist (`frontend/src/pages/PortfolioPage.tsx`, `frontend/src/config/primaryAreas.ts`, `frontend/src/components/PrimaryNav.tsx`, `backend/app/db/models.py`, `backend/app/main.py`, `frontend/vite.config.ts`) per plan.md
- [X] T002 [P] Create package layout `backend/app/portfolio/` (`__init__.py`) and confirm `backend/tests/unit/`, `backend/tests/contract/` ready for portfolio test files
- [X] T003 [P] Create frontend stubs `frontend/src/features/portfolio/` and `frontend/src/services/portfolioApi.ts` (types/placeholder exports only) per plan.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Models, capital identity, repository, read service/API, proxy — blocks all user stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [X] T004 Add `PortfolioRow` singleton and `PortfolioAllocationRow` in `backend/app/db/models.py` and ensure `init_db` / light migration creates tables per `data-model.md`
- [X] T005 [P] Implement capital identity helpers (`available = cash − reserved`, decimal-string compare) in `backend/app/portfolio/identity.py` per research Decision 3 / FR-003
- [X] T006 Implement portfolio + allocation load/save in `backend/app/portfolio/repository.py` (singleton portfolio `id=1`; allocation CRUD) per `data-model.md`
- [X] T007 Implement portfolio snapshot assembly + fail-closed load in `backend/app/portfolio/service.py` (`GET` read model: derived reserved/available/equity; deployed `"0"`; positions `[]`; optional `warning`; **never** call simulation/backtest/comparison start/stop) per research Decisions 1–2 / FR-001 / FR-004
- [X] T008 Implement `GET /portfolio` and mount router in `backend/app/api/portfolio.py` and `backend/app/main.py` per `contracts/portfolio-api.md`
- [X] T009 [P] Add Vite proxy `/portfolio` → backend in `frontend/vite.config.ts`
- [X] T010 [P] Unit tests: identity math, reserved sum, fail-closed corrupt load does not invent capital, service does not invoke trading in `backend/tests/unit/test_portfolio_service.py` (and/or `test_portfolio_identity.py`)
- [X] T011 [P] Contract tests: empty/unfunded `GET /portfolio` returns cash `"0"`, empty allocations, deployed `"0"`, positions `[]` in `backend/tests/contract/test_portfolio_api.py`
- [X] T012 Run baseline create-API smoke: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q` must pass before Portfolio UI wiring

**Checkpoint**: Read path + persistence foundation ready; stories can build funding, allocations, UI

---

## Phase 3: User Story 1 - Inspect authoritative portfolio capital (Priority: P1) 🎯 MVP

**Goal**: Operator can fund the local portfolio and inspect equity, cash, available, reserved, deployed, P&L, and positions with clear labels/units (deployed 0 / positions empty in 009).

**Independent Test**: Fund cash to a known value; open Portfolio → categories visible and reconcile (`available = cash − reserved`); deployed is 0; positions empty. (Funding reject when reserved > 0 is validated in US2 / T025.)

### Tests for User Story 1

- [X] T013 [P] [US1] Contract tests for `PUT /portfolio/funding` when reserved is 0: valid set updates cash; negative/invalid rejected; prior state unchanged on reject in `backend/tests/contract/test_portfolio_api.py` (extend). Do **not** require allocations here — `cash < reserved` coverage is T025 after US2 create exists.
- [X] T014 [P] [US1] Frontend tests in `frontend/src/__tests__/portfolio.test.tsx`: Portfolio loads snapshot; funding form sets cash and shows available; labels/units present; non-hover help for available/reserved/deployed; ~375px fund action usable per FR-010–FR-011 / SC-006 / `docs/UI_UX_STANDARDS.md`

### Implementation for User Story 1

- [X] T015 [US1] Implement `PUT /portfolio/funding` in `backend/app/api/portfolio.py` + `backend/app/portfolio/service.py` per `contracts/portfolio-api.md` / FR-001a (reject `cash < reserved`)
- [X] T016 [P] [US1] Implement `getPortfolio` / `putPortfolioFunding` client in `frontend/src/services/portfolioApi.ts`
- [X] T017 [US1] Expand `frontend/src/pages/PortfolioPage.tsx` (+ `frontend/src/features/portfolio/`) to show capital snapshot (equity, cash, available, reserved, deployed, realized/unrealized P&L, positions empty state) and funding action with busy/error/success feedback; remove thin “simulation-only summary” as the sole Portfolio content per FR-010
- [X] T018 [US1] Run T010–T014; fix until passing

**Checkpoint**: MVP — portfolio can be funded and inspected

---

## Phase 4: User Story 2 - Create and manage explicit capital allocations (Priority: P1)

**Goal**: Operator can create, resize, and release allocations under capital invariants; over-reserve rejected; shared `targetRef` allowed.

**Independent Test**: With cash `1000`, create two allocations totaling ≤ available; reject overspend; resize/release frees capital; duplicate `targetRef` allowed.

### Tests for User Story 2

- [X] T019 [P] [US2] Contract tests: `POST`/`PATCH`/`DELETE` allocations; over-reserve `400` leaves prior; same `targetRef` on two allocations allowed; snapshot invariants after each mutation in `backend/tests/contract/test_portfolio_api.py` (extend)
- [X] T020 [P] [US2] Frontend tests: create/resize/release flows; overspend error visible; confirm before release; busy prevents double submit in `frontend/src/__tests__/portfolio.test.tsx` (extend) per UI standards

### Implementation for User Story 2

- [X] T021 [US2] Implement allocation create/resize/release in `backend/app/portfolio/service.py` + `backend/app/portfolio/repository.py` enforcing FR-002 / FR-003 / FR-006
- [X] T022 [US2] Implement `POST /portfolio/allocations`, `PATCH /portfolio/allocations/{id}`, `DELETE /portfolio/allocations/{id}` in `backend/app/api/portfolio.py` per `contracts/portfolio-api.md`
- [X] T023 [P] [US2] Extend `frontend/src/services/portfolioApi.ts` with create/resize/release clients
- [X] T024 [US2] Build allocation list + create/resize/release UI in `frontend/src/features/portfolio/` wired from `PortfolioPage.tsx` (label, reservedSize, optional targetRef; confirm on release)
- [X] T025 [US2] Contract + UI proof for funding reject when reserved > 0: after at least one allocation exists, `PUT /portfolio/funding` with `cash < reserved` returns `400` and leaves prior state; Portfolio funding UI surfaces the clear error message (extends `backend/tests/contract/test_portfolio_api.py` and `frontend/src/__tests__/portfolio.test.tsx`) per FR-001a
- [X] T026 [US2] Assert mutating portfolio endpoints never call simulation/backtest/comparison create/start in unit/contract tests (`backend/tests/unit/test_portfolio_service.py` and/or contract spies)
- [X] T027 [US2] Run T019–T020; fix until passing

**Checkpoint**: SC-002 / SC-004 — safe allocations under capital identity

---

## Phase 5: User Story 3 - Inspect allocation-level accounting (Priority: P2)

**Goal**: Each allocation shows its own identity and reserved size (and zero/no-activity performance placeholders) while portfolio totals remain authoritative.

**Independent Test**: Two allocations with different sizes; inspect each; portfolio totals still reconcile; no double-counted equity.

### Tests for User Story 3

- [X] T028 [P] [US3] Frontend test: allocation cards/details show id/label/reservedSize and parent portfolio context without implying strategy-owned wallets in `frontend/src/__tests__/portfolio.test.tsx` (extend)

### Implementation for User Story 3

- [X] T029 [US3] Add allocation detail/summary presentation in `frontend/src/features/portfolio/` (reserved size mandatory; no-activity P&L/performance placeholders when undeployed) per FR-005 / US3
- [X] T030 [US3] Ensure portfolio summary and allocation list cannot double-count equity in display helpers under `frontend/src/features/portfolio/`
- [X] T031 [US3] Run T028; fix until passing

**Checkpoint**: Allocation inspection within one portfolio

---

## Phase 6: User Story 4 - Persist for inspection and reproducibility (Priority: P1)

**Goal**: After reload, last valid portfolio cash and allocations remain inspectable; rejected mutations never persist.

**Independent Test**: Fund + allocate; reload app/API → same state; invalid mutation then reload → last good state.

### Tests for User Story 4

- [X] T032 [P] [US4] Contract/integration style persistence test: fund + create allocation; new DB session/`GET` returns same cash/allocations; failed over-reserve then `GET` unchanged in `backend/tests/contract/test_portfolio_api.py` (extend) per FR-007 / FR-008 / SC-003

### Implementation for User Story 4

- [X] T033 [US4] Verify repository writes are transactional per mutation (no partial allocation+cash corruption) in `backend/app/portfolio/repository.py` / `service.py`
- [X] T034 [US4] Implement Portfolio UI display of GET snapshot `warning` when present (fail-closed recovery message visible, not hover-only) in `frontend/src/pages/PortfolioPage.tsx` / `frontend/src/features/portfolio/` per data-model fail-closed rules
- [X] T035 [US4] Run T032; fix until passing

**Checkpoint**: SC-003 — persistence + leave-last-good

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, docs, roadmap, UX gate

- [X] T036 [P] Re-run Simulation/Backtest contract suites green: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q` per FR-009 / SC-005
- [X] T037 [P] Frontend portfolio tests + relevant regression: `npm test -- --run src/__tests__/portfolio` (and quick sanity on existing Auto Trading tests if touched)
- [X] T038 Execute quickstart automated checks in `specs/009-portfolio-capital-allocation/quickstart.md` and fix gaps
- [X] T039 [P] Review Portfolio UI against `docs/UI_UX_STANDARDS.md` checklist (labels/units, help, validation, busy, confirm release, 375px, Simulation-not-real-money clarity)
- [X] T040 [P] At the start of `/speckit-implement`, set Feature 009 status to `IN PROGRESS` in `docs/ROADMAP.md` (table + section Status). Do **not** mark DONE until the completion audit gates pass
- [X] T041 Confirm no credentials/real-money/strategy balance mutation surfaces in portfolio code paths (`backend/app/portfolio/`, `backend/app/api/portfolio.py`, `frontend/src/features/portfolio/`)
- [X] T042 Propose commit message for Feature 009 work (do not auto-commit unless asked)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies
- **Phase 2 (Foundational)** → after Setup; **blocks all stories**
- **Phase 3 (US1)** → after Foundational — MVP fund + inspect
- **Phase 4 (US2)** → after US1 funding path (needs cash to allocate meaningfully)
- **Phase 5 (US3)** → after US2 (needs allocations to inspect)
- **Phase 6 (US4)** → after Foundational; strengthens with US1/US2 mutations present
- **Phase 7 (Polish)** → after desired stories complete

### User Story Dependencies

```text
Foundational
     │
     ▼
   US1 Fund + Inspect (MVP)
     │
     ▼
   US2 Allocations ──────────► US3 Allocation inspect
     │
     └──────────────────────► US4 Persistence proofs
```

- **US1**: Independent after foundation
- **US2**: Depends on US1 funding (practically)
- **US3**: Depends on US2 allocations
- **US4**: Mostly verification; needs write paths from US1/US2 for strong proofs

### Parallel Opportunities

- T002/T003; T005/T009/T010/T011 after models exist
- Within US1: T013/T014/T016 parallel with care
- Within US2: T019/T020/T023 parallel after service contracts sketched
- Polish T036/T037/T039 can parallel

---

## Parallel Example: User Story 2

```text
# After T021–T022 sketched:
T019 Contract allocation tests
T020 Frontend allocation UI tests
T023 portfolioApi allocation clients
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2: Setup + foundation (`GET /portfolio`)
2. Phase 3: Funding + Portfolio inspect UI
3. **STOP and VALIDATE**: Fund → reload → same cash; categories visible
4. Demo MVP

### Incremental Delivery

1. Foundation → read snapshot
2. US1 → fund + inspect MVP
3. US2 → allocations under invariants
4. US3 → allocation inspection polish
5. US4 → persistence proofs
6. Polish → quickstart green, UX checklist, regression

### Suggested MVP scope

**US1 only** (fund + inspect capital snapshot). US2 is the core product payoff and should follow immediately in the same feature delivery.

---

## Notes

- [P] = different files, no incomplete dependencies
- [USn] maps to spec user stories 1–4
- Commit only when asked; keep portfolio free of trading authority
- Do not migrate Simulation/Backtest fill ledgers in this feature
- Money amounts remain decimal strings (USDT-oriented)

---

## Task Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 42 |
| **US1** | 6 (T013–T018) |
| **US2** | 9 (T019–T027) |
| **US3** | 4 (T028–T031) |
| **US4** | 4 (T032–T035) |
| **Setup + Foundational + Polish** | 19 (T001–T012, T036–T042) |
| **Parallel opportunities** | Yes — marked [P] across phases |

**Format validation**: All tasks use `- [ ]`, Task IDs T001–T042, [P]/[USn] where required, and file paths in descriptions.

---

## Phase 8: Convergence

**Purpose**: Close gaps found by `/speckit-converge` against spec, plan, and constitution (post-implement assessment).

- [X] T043 CRITICAL: Harden `GET` / `build_snapshot` fail-closed path in `backend/app/portfolio/service.py` so a corrupt allocation `reservedSize` cannot invent available capital (today corrupt rows are skipped from the reserved sum while cash stays intact → inflated `available`); keep a clear `warning` and safe posture per edge-case fail-closed / FR-003 / Constitution I / Constitution VIII (`contradicts`)
- [X] T044 CRITICAL: Map corrupt/unparseable reserved sizes during funding and allocation create/resize in `backend/app/portfolio/service.py` to `PortfolioError` (clear `400` message) instead of uncaught `CapitalIdentityError` (`500`); leave prior persisted state unchanged; add unit/contract coverage in `backend/tests/unit/test_portfolio_service.py` and/or `backend/tests/contract/test_portfolio_api.py` per FR-008 / Constitution VIII (`partial`)
- [X] T045 [P] Review unused `allocationsDoNotAffectEquity` in `frontend/src/features/portfolio/capitalDisplay.ts` (and export in `index.ts`): wire into US3/display tests or remove dead helper per T030 / FR-005 (`unrequested`)
