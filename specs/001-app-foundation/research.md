# Research: Application Foundation

**Feature**: `001-app-foundation`  
**Date**: 2026-08-08

## Decision 1: Backend framework

**Decision**: Python 3.12+ with FastAPI and Uvicorn.

**Rationale**: Constitution requires Python. FastAPI is lightweight, provides clear HTTP contracts for health checks, and stays simple for a foundation that will later host trading APIs. Aligns with Intentional Simplicity (X).

**Alternatives considered**:
- Django: heavier for a health-only foundation; more ceremony than needed.
- Flask: viable but fewer built-in OpenAPI/typing benefits for later contracts.
- Pure ASGI without framework: too sparse for maintainability.

## Decision 2: Frontend stack

**Decision**: React 18+ with TypeScript and Vite.

**Rationale**: Constitution requires React. Vite is the conventional local-dev path with fast refresh and simple proxy to the backend. TypeScript reduces navigation/route mistakes early.

**Alternatives considered**:
- Create React App: deprecated tooling path.
- Next.js: unnecessary SSR/hosting complexity for a local-first shell.
- Plain JS without TypeScript: faster start, higher drift risk as routes grow.

## Decision 3: Persistence in this feature

**Decision**: Do **not** introduce domain database schemas or trading tables in this feature. Document SQL/SQLite as the persistence direction for later features. Foundation health is process/application readiness only (no DB dependency).

**Rationale**: Spec FRs require no portfolio/trading data. Adding empty schemas or unused ORM wiring violates Intentional Simplicity (X) and FR-010/FR-011. Constitution SQL requirement is satisfied as an architectural commitment for when persistence is first needed—not as premature scaffolding.

**Alternatives considered**:
- Ship SQLAlchemy + empty SQLite file now: extensible but unused complexity.
- Health checks that require DB connectivity: over-scopes SC-004/SC-005 and fails if DB unused.

## Decision 4: Repository layout

**Decision**: Dual-package web layout at repo root: `backend/` and `frontend/`, plus root `README.md` for local run steps.

**Rationale**: Matches constitution stack split, keeps boundaries clear for later exchange adapters (backend-only), and matches Spec Kit plan template web-application structure.

**Alternatives considered**:
- Monorepo with `apps/` and `packages/`: overkill for current team/scope.
- Single fullstack framework: conflicts with explicit Python + React split.

## Decision 5: Unknown-route behavior (unresolved in clarify)

**Decision**: Dedicated not-found view that keeps primary navigation visible (Dashboard / Auto Trading / Portfolio). Do **not** silent-redirect to Dashboard.

**Rationale**: Clarify session recommended this option; FR-012 allows either path. Explicit not-found is easier to test and debug during foundation work and avoids rewriting invalid URLs silently.

**Alternatives considered**:
- Auto-redirect to Dashboard: simpler UX, hides mistakes.
- Redirect with toast: extra UI state for little foundation value.

## Decision 6: Health exposure

**Decision**: Backend exposes `GET /health` returning a clear healthy payload when the process is up. Frontend does **not** require a Dashboard health widget for acceptance; developers/tests call the endpoint directly (and quickstart documents curl/browser check). Optional tiny status indicator is deferred.

**Rationale**: User Story 4 lists developer, frontend, or automated checks as consumers—not a mandatory UI surface. Spec SC-004/SC-005 are technology-agnostic verification outcomes. Avoid Dashboard clutter that could be mistaken for trading readiness.

**Alternatives considered**:
- Always show health on Dashboard: helpful ops UX, but not required and risks “system looks live/trading-ready” confusion.
- Frontend-only fake healthy flag: violates FR-008.

## Decision 7: Routing & default entry

**Decision**: Client-side routes for `/` (or `/dashboard`) → Dashboard, `/auto-trading`, `/portfolio`, plus catch-all → Not Found. Default entry resolves to Dashboard per clarification.

**Rationale**: Spec FR-002 and Clarifications session. Deep-link/refresh must preserve area (edge case).

**Alternatives considered**:
- Hash routing only: works but less conventional for Vite SPA; history API is fine for local/dev.

## Decision 8: Responsive navigation

**Decision**: Single primary nav pattern that works at ~375px (e.g., compact top or bottom nav with three labeled targets). No desktop-only hover-only navigation.

**Rationale**: Constitution XIV and SC-003. Keep visual design minimal; polish is out of scope.

**Alternatives considered**:
- Hamburger-only with hidden labels: risks failing “clearly identifiable” on phone.
- Separate mobile app: out of scope.

## Decision 9: Testing approach

**Decision**:
- Backend: `pytest` + HTTP client tests for health contract.
- Frontend: lightweight component/route tests (Vitest + React Testing Library) for navigation identity and placeholder absence of trading content; manual/quickstart viewport check for SC-003.

**Rationale**: Trading-critical tests (XXVIII) do not yet apply; foundation still needs automated coverage for health and navigable shell. Full E2E browser suite deferred to keep scope small.

**Alternatives considered**:
- Playwright E2E only: stronger SC-003 proof, higher setup cost for foundation.
- No automated tests: conflicts with “verify backend healthy” and later Spec Kit discipline.

## Decision 10: Local run documentation

**Decision**: Root README documents prerequisite tools (Python, Node), how to start backend and frontend, default URLs, and how to verify health + three areas.

**Rationale**: SC-001 and FR-001 require documented local runnability.

**Alternatives considered**:
- Docker Compose only: useful later; not required for success criteria and adds ops surface.
- Makefile-only without README: harder for first-time developers.
