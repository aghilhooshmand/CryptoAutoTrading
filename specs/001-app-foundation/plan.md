# Implementation Plan: Application Foundation

**Branch**: `001-app-foundation` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-app-foundation/spec.md`

## Summary

Establish a minimal, locally runnable CryptoAutoTrading foundation: a Python
3.12 backend with a health capability and a React frontend shell with exactly
three placeholder primary areas (Dashboard, Auto Trading, Portfolio) at
canonical routes `/dashboard`, `/auto-trading`, and `/portfolio` (`/` resolves
to Dashboard), responsive navigation, and a not-found recovery path—without any
trading, market, portfolio, sentiment, or auth behavior.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + Uvicorn (backend); Vite + React Router +
Lucide React (frontend; decorative primary-nav icons only)

**Storage**: N/A for this feature (no domain persistence). Future persistence
MUST be SQL (SQLite locally per constitution); not scaffolded with unused
schemas here.

**Testing**: pytest (backend health contract); Vitest + React Testing Library
(frontend navigation/placeholders)

**Target Platform**: Local developer machines (Linux/macOS/Windows) via browser;
phone-width validation at ~375px viewport

**Project Type**: Web application (separate backend + frontend)

**Performance Goals**: Health check responds in under 2 seconds locally
(SC-004); primary navigation across three areas under 30 seconds (SC-002)

**Constraints**: No XT/exchange, market data, strategies, trading control, risk,
simulation/real money, portfolio math, news, sentiment, backtesting, AI/ML, or
Google auth. No mocked trading UI. No auto-activation of real-money concepts.
Credentials must never appear in frontend or Git.

**Scale/Scope**: Single local developer/operator; three primary UI areas + health
endpoint; documentation for local run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No trading/capital risk introduced |
| II Simulation before real money | Pass | Neither mode implemented; no auto real-money |
| III–IV Trading pipeline / controller authority | Pass | Pipeline not implemented; no strategy→order paths |
| V–IX Session bounds, P&L, journals, fail-safe, stop | Pass | Deferred; not in foundation scope |
| X Intentional simplicity | Pass | Minimal shell + health only |
| XI–XII Strategies / no guaranteed profit | Pass | Placeholders; no profit claims or fake P&L |
| XIII Exactly three primary UI areas | Pass | Dashboard, Auto Trading, Portfolio at `/dashboard`, `/auto-trading`, `/portfolio` |
| XIV Responsive UX | Pass | Phone-width nav required |
| XV Python / React / SQL direction | Pass | Python 3.12 + React now; SQL deferred until first data feature |
| XVI–XVIII Exchange adapter / credentials / withdrawals | Pass | No exchange or credentials |
| XIX–XXVI Market sentiment | Pass | No sentiment UI/data (Dashboard placeholder only) |
| XXVII–XXIX Spec-driven / tests / source of truth | Pass | Spec→plan; automated health + nav tests planned |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — no unjustified complexity. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-app-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── health.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry
│   └── api/
│       ├── __init__.py
│       └── health.py     # GET /health
└── tests/
    ├── contract/
    │   └── test_health.py
    └── unit/

frontend/
├── package.json
├── vite.config.ts
├── vitest.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── config/
│   │   └── primaryAreas.ts
│   ├── components/
│   │   ├── AppShell.tsx
│   │   └── PrimaryNav.tsx   # labels + Lucide icons (LayoutDashboard, Bot, Wallet)
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── AutoTradingPage.tsx
│   │   ├── PortfolioPage.tsx
│   │   └── NotFoundPage.tsx
│   └── __tests__/        # navigation & placeholder checks

README.md                 # Local run + verification steps
```

**Structure Decision**: Web application with `backend/` and `frontend/` at
repository root. Keeps Python and React boundaries clear for later
backend-only credentials and exchange adapters. No `src/` monolith.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 & Phase 1 Outputs

- [research.md](./research.md) — stack, routing, health, unknown-route, persistence decisions
- [data-model.md](./data-model.md) — Primary Area and Backend Health Status
- [contracts/health.md](./contracts/health.md) — `GET /health` contract
- [quickstart.md](./quickstart.md) — local validation scenarios

## Post-Design Constitution Re-check

Design remains a placeholder shell + health contract. No trading pipeline,
sentiment, credentials, or persistence schemas introduced. **PASS**.
