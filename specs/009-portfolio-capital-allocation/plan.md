# Implementation Plan: Portfolio & Capital Allocation Core

**Branch**: `009-portfolio-capital-allocation` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-portfolio-capital-allocation/spec.md`  
(including Session 2026-08-14 clarifications)

## Summary

Add an authoritative **local portfolio** capital model with explicit
**allocations** (reservations), independent of strategy logic. Persist
portfolio cash/equity and allocation rows in SQLite behind a thin `/portfolio`
API. Operator funds cash via controlled Portfolio actions, creates/resizes/
releases allocations under `available = cash − reserved`, and inspects capital
categories (deployed/positions first-class but **0/empty** until later binding).
Expand the existing primary **Portfolio** page. Do not migrate Simulation/
Backtest ledgers or enable real-money trading.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: Existing FastAPI + SQLAlchemy + SQLite; Vite + React.
Reuse decimal-string money patterns from Simulation accounting. New
`app.portfolio` package + API + Portfolio UI only. No second trading engine.

**Storage**: SQLite in the shared local DB (`backend/data/simulation.db`):
- singleton `portfolio` row (cash, realized/unrealized P&L placeholders, etc.)
- `portfolio_allocations` table (one row per allocation)
No portfolio history versioning in v1 beyond current effective state.

**Testing**: pytest unit (capital identity, over-reserve reject, funding reject
when cash would fall below reserved, corrupt fail-closed) + contract
(`GET`/`funding`/`allocations` CRUD); Vitest Portfolio page (fund, allocate,
reject overspend, ~375px, help for capital terms). Existing Simulation/Backtest
regression suites remain green.

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Local DB ops only; no dedicated SLO gate.

**Constraints**:
- Explicit Portfolio funding (not Settings / Simulation mirror)
- `available = cash − reserved`; `reserved ≤ cash`; `available ≥ 0`
- Deployed = 0 and positions empty in Feature 009 (still visible)
- Allocations are reservations; do not start trading
- Target references optional and non-unique
- Reject funding cuts that would make `cash < reserved`
- Strategies never mutate portfolio balances/positions
- No Simulation/Backtest ledger migration; no historical rewrite
- No XT private, real money, leverage, short, margin, multi-exchange, Torque/GE
- UI inherits `docs/UI_UX_STANDARDS.md`; Portfolio primary nav only
- Package path locked: `backend/app/portfolio/`

**Scale/Scope**: Single local operator; one portfolio; N allocations (small)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Hard reserve/funding invariants; fail closed |
| II Simulation before real money | Pass | No real-money path; sim unchanged |
| III–IV Pipeline / controller–risk | Pass | Portfolio never bypasses pipeline; strategies advisory |
| V Explicit session boundaries | Pass | Allocations ≠ trading sessions |
| VI Net P&L | Pass | Realized/unrealized fields present; no fake fills |
| VII Decision traceability | Pass | Persist effective portfolio/allocation state |
| VIII Fail safe | Pass | Invalid updates rejected; corrupt load fail-closed |
| IX Emergency stop | Pass | N/A; no live trading control here |
| X Intentional simplicity | Pass | Thin portfolio package + primary Portfolio UI |
| XI Conventional strategies | Pass | Target refs optional; no strategy mutation |
| XII Evidence, not guarantees | Pass | No profit claims |
| XIII Three primary UI areas | Pass | Uses existing Portfolio nav |
| XIV Operator UI / responsive | Pass | Labels/units/help; ~375px; UX standards |
| XV Python / React / SQL | Pass | SQLite |
| XVI–XVIII Adapter / credentials | Pass | No credentials |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Contracts + unit/contract/UI tests |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |
| XXXIII Settings ≠ history | Pass | Settings not the portfolio ledger |
| XXXIV Portfolio/allocation authority | Pass | Explicit allocations; strategies cannot invent capital |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Design adds portfolio singleton +
allocation rows and a funding/allocation API with capital identity checks;
Controller/Risk/Execution and Simulation/Backtest accounting remain
authoritative for trading fills; Feature 009 does not enable real money.

## Project Structure

### Documentation (this feature)

```text
specs/009-portfolio-capital-allocation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── portfolio-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   └── portfolio.py             # NEW — portfolio + allocations API
│   ├── portfolio/                   # NEW package (canonical: app.portfolio)
│   │   ├── service.py               # Funding + allocate/resize/release + invariants
│   │   ├── repository.py            # Portfolio + allocation persistence
│   │   └── identity.py              # available = cash − reserved helpers
│   ├── db/models.py                 # ADD PortfolioRow, PortfolioAllocationRow
│   └── main.py                      # Mount portfolio router
├── tests/
│   ├── unit/test_portfolio_*.py
│   └── contract/test_portfolio_api.py
frontend/
├── src/
│   ├── pages/PortfolioPage.tsx      # EXPAND — capital snapshot + allocations UI
│   ├── features/portfolio/          # NEW — panels/forms for fund + allocate
│   ├── services/portfolioApi.ts     # NEW
│   └── __tests__/portfolio*.test.tsx
└── vite.config.ts                   # Proxy /portfolio
```

**Structure Decision**: Web app layout matching Feature 008 (`app.settings`
pattern). Portfolio lives under primary Portfolio route, not Auto Trading tabs.

## Complexity Tracking

> No constitution violations requiring justification.
