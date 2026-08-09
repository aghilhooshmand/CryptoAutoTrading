# Tasks: Application Foundation
      
**Input**: Design documents from `/specs/001-app-foundation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included where plan.md / research.md / quickstart.md require automated verification (backend health contract; frontend navigation & placeholders).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `README.md` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create repository directories `backend/app/api/`, `backend/tests/contract/`, `backend/tests/unit/`, `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/config/`, and `frontend/src/__tests__/` per plan.md
- [x] T002 [P] Add root `.gitignore` covering Python venvs, `__pycache__`, Node `node_modules/`, build outputs, `.env` files, and OS junk (no secrets committed)
- [x] T003 [P] Initialize Python 3.12 backend project with FastAPI, Uvicorn, and pytest in `backend/pyproject.toml`
- [x] T004 [P] Initialize React 18 + TypeScript + Vite frontend in `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, and `frontend/index.html`
- [x] T005 [P] Add frontend React Router dependency and baseline scripts (`dev`, `build`, `test`) in `frontend/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Minimal runnable app shells and shared routing constants that ALL user stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create FastAPI application entry in `backend/app/main.py` that starts with Uvicorn and mounts an empty/ready API router
- [x] T007 [P] Create API package markers `backend/app/__init__.py` and `backend/app/api/__init__.py`
- [x] T008 Create frontend entry `frontend/src/main.tsx` and root `frontend/src/App.tsx` with React Router provider
- [x] T009 Define Primary Area route constants (`/dashboard`, `/auto-trading`, `/portfolio`) and `/` → Dashboard resolution helper in `frontend/src/config/primaryAreas.ts` per data-model.md
- [x] T010 Create `frontend/src/components/AppShell.tsx` product chrome (product name CryptoAutoTrading + outlet for page content) without trading widgets
- [x] T011 Create `frontend/src/components/PrimaryNav.tsx` with links to the three canonical primary routes (labels: Dashboard, Auto Trading, Portfolio)

**Checkpoint**: Foundation ready — backend and frontend skeletons exist; user story implementation can begin

---

## Phase 3: User Story 1 - Run the application locally (Priority: P1) 🎯 MVP

**Goal**: A developer can start backend and frontend locally, open the UI, land on Dashboard, and see the product shell with primary navigation.

**Independent Test**: Follow documented start steps; open the app; confirm shell loads, default entry is Dashboard, primary nav is visible.

### Implementation for User Story 1

- [x] T012 [US1] Wire `AppShell` + `PrimaryNav` into `frontend/src/App.tsx` routes so `/` resolves to Dashboard and `/dashboard` renders a minimal Dashboard outlet
- [x] T013 [US1] Add minimal `frontend/src/pages/DashboardPage.tsx` so the default entry is not a blank/broken page (placeholder-only; no market/trading/sentiment data)
- [x] T014 [US1] Document local prerequisites (Python 3.12, Node LTS), backend start, frontend start, and default URLs in root `README.md`
- [x] T015 [US1] Verify both processes start cleanly and the browser reaches the shell without exchange credentials (manual check against FR-001 / SC-001)

**Checkpoint**: Local run works; MVP shell reachable at `/` → Dashboard

---

## Phase 4: User Story 2 - Navigate the three primary areas (Priority: P1)

**Goal**: Users can move among Dashboard, Auto Trading, and Portfolio with clear labels, active state, placeholder-only content, and a not-found recovery path.

**Independent Test**: Visit each primary area via nav; confirm labels and placeholder messaging; open an unknown path and recover via primary nav.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T016 [P] [US2] Add Vitest + React Testing Library config in `frontend/vitest.config.ts` and a sample setup file if needed
- [x] T017 [P] [US2] Write navigation/placeholder tests in `frontend/src/__tests__/primaryNavigation.test.tsx` asserting `/dashboard`, `/auto-trading`, `/portfolio`, active area, and absence of mocked trading/P&L/market/sentiment content
- [x] T018 [P] [US2] Write not-found recovery test in `frontend/src/__tests__/notFound.test.tsx` asserting unknown paths show not-found while primary nav remains usable

### Implementation for User Story 2

- [x] T019 [P] [US2] Implement placeholder `frontend/src/pages/AutoTradingPage.tsx` (coming-later messaging only; no strategies/sessions/trades)
- [x] T020 [P] [US2] Implement placeholder `frontend/src/pages/PortfolioPage.tsx` (coming-later messaging only; no balances/positions/P&L)
- [x] T021 [P] [US2] Implement `frontend/src/pages/NotFoundPage.tsx` with clear not-found copy and primary nav still available (no silent redirect)
- [x] T022 [US2] Complete route table in `frontend/src/App.tsx`: `/` → Dashboard, `/dashboard`, `/auto-trading`, `/portfolio`, catch-all → NotFound; highlight active area in `frontend/src/components/PrimaryNav.tsx`
- [x] T023 [US2] Refine `frontend/src/pages/DashboardPage.tsx` placeholder copy so it does not imply live trading readiness or guaranteed profit (FR-005)
- [x] T024 [US2] Ensure deep-link/refresh preserves the current primary area for `/dashboard`, `/auto-trading`, and `/portfolio` (SPA history routing)
- [x] T025 [US2] Run frontend tests and fix until T017–T018 pass

**Checkpoint**: All three areas navigable with placeholders; unknown routes fail closed to not-found

---

## Phase 5: User Story 3 - Use the shell on phone-sized screens (Priority: P2)

**Goal**: At ~375px width, primary navigation remains reachable and all three areas stay identifiable/readable.

**Independent Test**: Resize to ~375px (or emulate); complete navigation among all three primary areas without desktop-only gestures.

### Implementation for User Story 3

- [x] T026 [US3] Add responsive layout/styles for the shell and nav in `frontend/src/components/AppShell.tsx` and/or `frontend/src/components/PrimaryNav.tsx` (and shared CSS module/file under `frontend/src/` as needed) usable at ~375px
- [x] T027 [US3] Verify labels/titles remain readable on Dashboard, Auto Trading, and Portfolio at phone width (manual quickstart Scenario C); adjust styles in the same shell/nav/page files if clipped
- [x] T028 [P] [US3] Add a lightweight responsive smoke assertion or documented viewport checklist note in `frontend/src/__tests__/responsiveNav.test.tsx` (or extend `primaryNavigation.test.tsx`) so nav targets remain present/accessible in a narrow viewport

**Checkpoint**: Phone-width navigation satisfies SC-003 / FR-006

---

## Phase 6: User Story 4 - Verify backend health (Priority: P2)

**Goal**: `GET /health` reports healthy when the backend is up; checks fail when the backend is down—no fake healthy UI.

**Independent Test**: With backend running, health returns healthy; with backend stopped, check does not report healthy.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T029 [P] [US4] Add pytest config/markers as needed in `backend/pyproject.toml`
- [x] T030 [US4] Write contract test for `GET /health` in `backend/tests/contract/test_health.py` expecting HTTP 200, JSON `{"status":"healthy"}`, and local completion in under 2 seconds (SC-004) per `specs/001-app-foundation/contracts/health.md`

### Implementation for User Story 4

- [x] T031 [US4] Implement health route handler in `backend/app/api/health.py` returning `{"status":"healthy"}`
- [x] T032 [US4] Register health router on the FastAPI app in `backend/app/main.py` at path `/health`
- [x] T033 [US4] Run contract tests until T030 passes (including SC-004 under-2-seconds assertion); manually confirm stopped-backend failure mode (SC-005 / FR-008) via documented curl in quickstart.md — do not add infrastructure solely to automate unreachable-process testing
- [x] T034 [US4] Document health URL, curl verification, SC-004 timing expectation, and manual stopped-backend check in root `README.md` (no Dashboard health widget required for Feature 001)

**Checkpoint**: Health contract satisfied; unavailable backend does not report healthy

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation alignment, scope guard, quickstart validation

- [x] T035 [P] Align root `README.md` with all quickstart scenarios A–H (routes, health, phone-width note, out-of-scope list)
- [x] T036 [P] Confirm no trading mocks, market data, sentiment, auth, exchange, or SQL schemas were introduced (scope guard FR-010/FR-011); remove any accidental stubs
- [x] T037 Run full `specs/001-app-foundation/quickstart.md` validation (local start, three routes, `/` → Dashboard, not-found, health up/down, phone-width)
- [x] T038 [P] Propose a concise Git commit message for the completed foundation work (do not auto-commit unless the user explicitly asks) per constitution XXX

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; practical dependency on US1 shell wiring (T012–T013) for a navigable app
- **User Story 3 (Phase 5)**: Depends on US2 pages/nav existing (responsive styles need the three areas)
- **User Story 4 (Phase 6)**: Depends on Foundational backend entry (T006); can proceed in parallel with US2/US3 after Foundational
- **Polish (Phase 7)**: Depends on US1–US4 intended scope complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US3/US4
- **US2 (P1)**: After Foundational (+ US1 shell recommended)
- **US3 (P2)**: After US2 navigation/pages exist
- **US4 (P2)**: After Foundational backend — independent of frontend stories

### Within Each User Story

- Tests (where included) MUST be written and FAIL before implementation
- Core routes/pages before polish copy
- Story complete before treating the next priority as done

### Parallel Opportunities

- T002, T003, T004, T005 in Setup can run in parallel
- T007 with early frontend work after T006 exists is limited; T007 is [P] with backend-only files
- After Foundational: US4 backend health can run in parallel with US2 frontend navigation
- T019, T020, T021 page stubs can run in parallel
- T016–T018 frontend tests can be authored in parallel before page implementation completes

---

## Parallel Example: User Story 2

```bash
# Author frontend tests together:
Task: "Write navigation/placeholder tests in frontend/src/__tests__/primaryNavigation.test.tsx"
Task: "Write not-found recovery test in frontend/src/__tests__/notFound.test.tsx"

# Implement placeholder pages together:
Task: "Implement placeholder frontend/src/pages/AutoTradingPage.tsx"
Task: "Implement placeholder frontend/src/pages/PortfolioPage.tsx"
Task: "Implement frontend/src/pages/NotFoundPage.tsx"
```

## Parallel Example: After Foundational

```bash
# Backend health (US4) alongside frontend navigation (US2):
Task: "Write contract test in backend/tests/contract/test_health.py"
Task: "Implement health route in backend/app/api/health.py"
Task: "Implement placeholder pages and routes in frontend/src/pages/* and App.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Local run + Dashboard shell
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → skeletons ready
2. US1 → locally runnable shell (MVP)
3. US2 → full three-area placeholders + not-found
4. US3 → phone-width usability
5. US4 → health contract
6. Polish → README + quickstart pass

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Developer A: US1 → US2 → US3 (frontend path)
   - Developer B: US4 (backend health)
3. Integrate at polish / quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- [Story] labels map to spec.md user stories US1–US4
- Do not add XT integration, market data, strategies, risk, simulation, real money, portfolio math, news, sentiment, backtesting, AI/ML, Google auth, or fake trading UI
- Prefer one coherent commit per meaningful unit; propose message; commit only when user asks (constitution XXX)
- Stop at any checkpoint to validate the story independently

---

## Phase 8: Convergence

**Purpose**: Close remaining gaps between Feature 001 artifacts and the current codebase

- [x] T039 Review unrequested Lucide primary-nav icons in `frontend/src/components/PrimaryNav.tsx` and `frontend/package.json`: either remove them to match Feature 001 spec/plan/tasks, or retain them and add a brief note in `README.md` that decorative Lucide icons (LayoutDashboard, Bot, Wallet) accompany nav labels without changing routes or placeholders per plan: Feature 001 scope (unrequested)
