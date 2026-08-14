# Implementation Plan: Portfolio & Capital Allocation Core

**Branch**: `009-portfolio-capital-allocation` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-portfolio-capital-allocation/spec.md`  
(including Session 2026-08-14 capital-reservation clarifications **and**
holdings/exchange-style clarifications)

## Summary

Extend the existing local portfolio domain into **one accounting book**:
exchange-style **holdings** (asset, quantity, cost basis when known, public
mark-to-market, weights, P&L where defined) plus explicit **quote-cash
reservations**. Quote cash **is** the USDT holding, not a second ledger.
`available = quote_cash − reserved`. Operator funds USDT, records local/manual
non-quote holdings, and manages allocations. Persist snapshots on meaningful
book changes for later analytics; Feature 009 UI stays current-state (no
equity curve / drawdown). Value holdings via Feature 002 public quotes; never
invent prices; mark equity **partial** when any holding is unvalued. Do not
migrate Simulation/Backtest fill ledgers, call XT private APIs, or execute
trades.

Existing 009 cash/allocation code is the foundation to **extend**, not replace.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: Existing FastAPI + SQLAlchemy + SQLite; Vite + React.
Reuse decimal-string money (`app.simulation.money`) and Feature 002
`MarketDataService.get_quote` / 60s fresh-vs-stale. Extend `app.portfolio`.
No second trading engine.

**Storage**: Shared local SQLite (`backend/data/simulation.db`):
- singleton `portfolio` (book metadata / timestamps)
- `portfolio_holdings` (one row per asset; USDT quantity **is** quote cash)
- `portfolio_allocations` (unchanged reservation rows)
- `portfolio_snapshots` (append-only on meaningful book mutations)

Light migration: copy existing `portfolio.cash` into a `usdt` holding once;
holding quantity becomes source of truth.

**Testing**: pytest unit (identity, valuation/partial equity, holdings CRUD,
snapshot-on-mutation-not-GET, fail-closed) + contract (`GET`, funding,
holdings, allocations); Vitest Portfolio (holdings table, fund, record
holding, allocate, partial/stale labels, ~375px). Simulation/Backtest
regression stays green.

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Local DB + a small number of public quote lookups per
GET; no dedicated SLO gate.

**Constraints**:
- One book: no parallel “capital portfolio” vs “asset portfolio”
- Quote cash = USDT holding quantity; funding cannot undercut reserved
- `available = quote_cash − reserved`; `reserved ≤ quote_cash`
- Local/manual holdings for supported non-quote assets; provenance required
- Valuation via public USDT-quoted prices; never invent; stale last-known
  included with stale flag; missing price excluded; equity marked partial
- Snapshots on funding / holdings / allocation mutations only — not price ticks
- 009 UI current-state only (no time-series charts)
- Deployed = 0; positions = [] until later pipeline binding
- Allocations reserve quote cash only; no trading side effects
- Strategies never mutate holdings/balances/allocations/P&L
- No Simulation/Backtest ledger migration; no XT private; no real money
- UI inherits `docs/UI_UX_STANDARDS.md`; existing Portfolio nav
- Package path locked: `backend/app/portfolio/`

**Scale/Scope**: Single local operator; one portfolio; small N holdings and
allocations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Quote-cash reserve/funding invariants; fail closed; no invented prices or balances |
| II Simulation before real money | Pass | No real-money path; sim ledgers unchanged |
| III–IV Pipeline / controller–risk | Pass | Holdings writes in 009 are operator funding/bootstrap only; strategies advisory; later fills still pipeline-only |
| V Explicit session boundaries | Pass | Allocations ≠ trading sessions; local holdings ≠ fills |
| VI Net P&L | Pass | P&L only when cost basis + value exist; no fake fills |
| VII Decision traceability | Pass | Persist holdings + allocations + snapshots on book changes |
| VIII Fail safe | Pass | Reject invalid updates; corrupt load fail-closed; partial equity labeled |
| IX Emergency stop | Pass | N/A; no live trading control here |
| X Intentional simplicity | Pass | Extend existing package; no terminal UI; no snapshot list API in 009 |
| XI Conventional strategies | Pass | No strategy mutation |
| XII Evidence, not guarantees | Pass | No profit claims; no fake history charts |
| XIII Three primary UI areas | Pass | Existing Portfolio nav |
| XIV Operator UI / responsive | Pass | Labels/units/help; provenance; ~375px |
| XV Python / React / SQL | Pass | SQLite |
| XVI–XVIII Adapter / credentials | Pass | Public market data only; no credentials |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Contracts + unit/contract/UI tests |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |
| XXXI Roadmap | Pass | 009 IN PROGRESS; holdings noted on roadmap |
| XXXIII Settings ≠ history | Pass | Settings not the portfolio ledger |
| XXXIV Portfolio/allocation authority | Pass | Explicit allocations; strategies cannot invent capital |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Design adds holdings + snapshot rows
and valuation against public quotes; quote-cash reservation API remains;
Controller/Risk/Execution stay authoritative for fills; Feature 012 can later
map XT private balances into the same holdings rows (different provenance).
Feature 009 does not enable real money or private XT.

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
└── tasks.md              # Created/updated by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/portfolio.py             # EXTEND — holdings + funding + allocations
│   ├── portfolio/                   # EXTEND
│   │   ├── identity.py              # quote_cash − reserved; equity sum
│   │   ├── valuation.py             # NEW — public quotes; partial/stale
│   │   ├── repository.py            # EXTEND holdings + snapshots
│   │   └── service.py               # EXTEND snapshot assembly + mutations
│   ├── db/models.py                 # ADD holdings + snapshot tables; migrate cash
│   └── market_data/                 # REUSE get_quote (no XT private)
├── tests/
│   ├── unit/test_portfolio_*.py
│   └── contract/test_portfolio_api.py
frontend/
├── src/
│   ├── pages/PortfolioPage.tsx      # EXPAND holdings + capital + allocations
│   ├── features/portfolio/          # EXTEND holdings panel
│   ├── services/portfolioApi.ts     # EXTEND
│   └── __tests__/portfolio*.test.tsx
└── vite.config.ts                   # /portfolio proxy (already present)
```

**Structure Decision**: Keep Feature 008-style `app.portfolio` package. Do not
split a second “assets” service. Portfolio stays on the primary Portfolio
route.

## Complexity Tracking

> No constitution violations requiring justification.
