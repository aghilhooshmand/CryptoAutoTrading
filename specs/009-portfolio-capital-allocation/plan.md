# Implementation Plan: Portfolio & Capital Allocation Core

**Branch**: `009-portfolio-capital-allocation` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Simulation Portfolio locked direction (2026-08-14). Operator funds
simulation USDT only. Non-USDT holdings come from simulated execution.
Capital reservation stays in the model but not as the dominant UI.

## Summary

**Rework of Feature 009** (Simulation Portfolio direction; do not start
Feature 010). Remaining correction work is tracked in `tasks.md`
(T044–T087). Operator-visible name: **Simulation Portfolio**.

Keep the existing `app.portfolio` package, USDT-as-quote-cash identity,
allocation CRUD, valuation, and snapshots. **Remove** the operator
local/manual holdings book (public `PUT`/`DELETE /portfolio/holdings` and
the holdings record form). **Add** fill→portfolio accounting on successful
Feature 003 Simulation fills. Relabel the UI as **Simulation Portfolio**:
summary cards, current-state allocation visual, holdings table/cards,
compact Capital section.

## Current implementation vs locked direction

### Reuse (keep)

| Area | Why it still fits |
|------|-------------------|
| `backend/app/portfolio/` identity, repository, valuation, snapshot assembly | One book; USDT holding = quote cash; `available = cash − reserved`; public quotes; fail-closed; snapshots on mutation |
| Allocation CRUD API | Constitution XXXIV; FR-002/003/006 |
| Funding `PUT /portfolio/funding` | Simulation USDT funding |
| SQLite tables `portfolio`, `portfolio_holdings`, `portfolio_allocations`, `portfolio_snapshots` | Same entities; provenance values change |
| Feature 002 `get_quote` | Valuation |
| Vite `/portfolio` proxy, Portfolio route | Shell |

### Contradicted the locked direction (corrected by T044–T087)

| Area | Contradiction (before correction) |
|------|----------------|
| `PUT`/`DELETE /portfolio/holdings` | Operator can type BTC/ETH |
| `HoldingsPanel` record/remove form | Manual holdings book |
| Copy: “local holdings book”, “local/manual”, “not real-money brokerage funding” | Sandbox wording |
| `bookProvenance` / holding `provenance` = `local_manual` | Must be `simulation` |
| USDT `unrealizedPnl: "0"` | No artificial USDT unrealized P&L |
| Dominant allocation panel | Must become compact Capital |
| No fill hook in `session_service._apply_fill` | BTC never appears from Simulation |
| `deployed` / `positions` always `"0"` / `[]` | Must reflect active Feature 003 long exposure |
| Tests that upsert BTC via public holdings API / UI form | Replace with fill-apply tests |

### Migration / rework

1. Treat existing `local_manual` rows as **simulation** on read (rewrite
   provenance on migrate or next mutation).
2. Remove public holdings upsert/delete routes.
3. Add `apply_simulation_fill` in `app.portfolio` and call it from Feature
   003 `_apply_fill` **after** the session journal row is added, still in the
   same SQLAlchemy session. Catch a refused apply (insufficient USDT or SELL
   qty exceeding the holding): do not roll back journals; persist
   `fillApplyWarning`; skip `simulation_fill` snapshot. Successful apply
   clears that warning. USDT moves by Feature 003 `cash_delta`; SELL
   `realizedPnl` uses `(fill_price − average_cost) × qty` (no second fee line).
4. On GET, derive `deployed` / `positions` from active Feature 003 sessions
   (`RUNNING` or `STOPPING` with a long position). Do not persist those as
   an operator-editable ledger.
5. Restyle Portfolio UI; current-state weight visual; holdings cards at ~375px;
   show GET `warning`.
6. Do **not** migrate Backtest journals. Do **not** rewrite historical
   Feature 003 journal rows.

## Technical Context

**Language/Version**: Python 3.12; TypeScript + React 18+

**Primary Dependencies**: FastAPI, SQLAlchemy, SQLite, Vite, React. Reuse
`app.simulation.money`, Feature 002 quotes, Feature 003 fill math
(`FillQuote`, `cash_delta`, qty, symbol).

**Storage**: Same SQLite tables. Provenance `simulation`. Snapshot reasons
add `simulation_fill` (keep funding / allocation_*). Drop operator
`holding_upsert` / `holding_delete` as public mutation reasons.

**Testing**: pytest unit (identity, valuation, **fill apply**, refused apply
leaves book unchanged + warning, fail-closed, no public holdings upsert,
deployed/positions from a long session); contract (GET, funding, allocations,
fill updates holdings, holdings PUT 404/405, GET `warning` after refused
apply); Vitest (summary, no asset-entry form, SIMULATION label, compact
capital including deployed, weights visual, warning banner, ~375px);
Simulation/Backtest regression green.

**Target Platform**: Local developer machines; ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Local DB + a small number of public quote lookups per GET

**Constraints**: Spec FR-001–FR-012. Package `backend/app/portfolio/`.
No XT private. No Feature 010.

**Scale/Scope**: One local operator; small N holdings and allocations

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Reservation identity; fail-closed fill apply |
| II Simulation before real money | Pass | 009 is Simulation Portfolio only |
| III–IV Pipeline | Pass | Fills applied only after Execution; strategies advisory |
| V Session boundaries | Pass | Journals kept even if portfolio apply is refused |
| VI Net P&L | Pass | Realized from sells; no fake fills |
| VII Traceability | Pass | Snapshots on funding/successful fill/allocation |
| VIII Fail safe | Pass | No invented prices/balances; no negative USDT; no journal rollback on refuse |
| X Simplicity | Pass | Extend package; remove manual holdings surface |
| XII Evidence | Pass | No history charts; current donut OK |
| XIII–XIV UI | Pass | Portfolio nav; summary cards; 375px |
| XVI–XVIII | Pass | Public quotes only |
| XXVII–XXXI | Pass | Spec/tests; 009 stays IN PROGRESS; propose commits |
| XXXIII | Pass | Settings ≠ portfolio |
| XXXIV | Pass | Allocations kept; strategies cannot invent capital |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Fill apply is Portfolio/Accounting after Execution, not a strategy
write. Refused apply does not invent negative USDT and does not undo Feature
003 journals (FR-009 attempt). Feature 013 still owns XT private. Feature
010 not started (including per-allocation deployed limits).

## Project Structure

### Documentation (this feature)

```text
specs/009-portfolio-capital-allocation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/portfolio-api.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/app/portfolio/                 # EXTEND — apply_simulation_fill
backend/app/api/portfolio.py           # REMOVE public holdings PUT/DELETE
backend/app/simulation/session_service.py  # CALL apply after _apply_fill
backend/tests/unit/test_portfolio_*.py
backend/tests/contract/test_portfolio_api.py
frontend/src/pages/PortfolioPage.tsx
frontend/src/features/portfolio/        # REWORK UI; remove asset-entry form
frontend/src/services/portfolioApi.ts
frontend/src/__tests__/portfolio.test.tsx
```

**Structure Decision**: Same `app.portfolio` package. No second holdings service.

## Complexity Tracking

> Dual session-cash vs portfolio-USDT during 009 is an explicit transitional
> assumption in the spec — not a second operator-editable book. The hook
> attempts apply in the same DB session after journals are written; refusal
> is caught so the session transaction still commits. GET `warning` is the
> operator-visible divergence signal. `deployed`/`positions` are a read-only
> projection of active Feature 003 longs, not stored portfolio rows.
