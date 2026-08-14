# Implementation Plan: Advanced Risk Management

**Branch**: `010-advanced-risk-management` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 010 MVP — one shared Risk authority; Simulation
Portfolio capital gates; optional allocation binding; one Portfolio max-loss
stop; optional per-symbol weight; shared reason catalog with fixed precedence;
Settings defaults only; Backtest keeps session Risk without live Portfolio
gates. Dual ledger retained. Daily loss / drawdown stop / wallet unification
out of scope.

## Summary

Extend the existing `RiskManager` / `RiskContext` (Feature 003/004) so
**Simulation** Risk can read Feature 009 Portfolio figures without a second
engine. Persist new effective risk fields on the Simulation session at
create/start. Catalogize reject/stop codes (stable code ≠ message) and enforce
first-fail precedence. Wire create/start `available` check, bound allocation
BUY remaining, Portfolio max-loss stop, optional per-symbol cap, and allocation
resize/release guards while bound. Backtest/Comparison continue using the same
`RiskManager` for session-style rules only (portfolio context absent/disabled).

## Technical Context

**Language/Version**: Python 3.12; TypeScript + React 18+

**Primary Dependencies**: FastAPI, SQLAlchemy, SQLite, Vite, React. Reuse
`app.simulation.control.risk.RiskManager`, `TradingController`, Feature 009
portfolio service/read model, Feature 008 Settings defaults copy-at-create,
Feature 002 public quotes for valuation.

**Storage**: Extend `simulation_sessions` (and Settings defaults row) with
nullable portfolio-aware risk fields + optional `allocation_id` binding.
No new risk engine tables. Portfolio tables unchanged except mutation guards
on allocation resize/release.

**Testing**: pytest unit (Risk precedence, portfolio gates, max-loss freeze,
per-symbol fail-closed); contract (Simulation create/start, journals codes,
allocation resize/release while bound); Backtest regression green; Vitest for
Simulation form fields + Settings optional defaults + journal reason display.

**Target Platform**: Local developer machines; ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Portfolio read + Risk review per closed candle; no
extra distributed systems

**Constraints**: Spec FR-001–FR-012 and clarify locks. One Risk authority.
No XT private. No Feature 011 rewrite. No daily/drawdown stops. Dual ledger.

**Scale/Scope**: One active Simulation; small N allocations/holdings

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Portfolio available at start; allocation remaining on BUY; portfolio max-loss |
| II Simulation before real money | Pass | Simulation-only portfolio gates; no real money |
| III–IV Pipeline / advisory strategies | Pass | Extend Risk after Controller; strategies never write |
| V Session boundaries | Pass | Session limits retained; portfolio stop stops that session |
| VI Net P&L | Pass | Portfolio loss uses known-value / quote-cash metrics; no invented prices |
| VII Traceability | Pass | Catalog codes + messages; journals; persisted effective config |
| VIII Fail safe | Pass | Incomplete valuation → reject BUYs; never invent stop/prices |
| IX Emergency stop | Pass | Remains first in precedence |
| X Simplicity | Pass | Extend RiskManager; no second engine |
| XII Evidence | Pass | No fake drawdown-stop charts |
| XIII–XIV UI | Pass | Auto Trading + Settings + Portfolio visibility; 375px |
| XVI–XVIII | Pass | Public quotes only |
| XXVII–XXXI | Pass | Spec/plan/tests; roadmap IN PROGRESS; propose commits only |
| XXXIII Settings defaults | Pass | Copy at create; no historical rewrite |
| XXXIV Portfolio allocation | Pass | Binding + reserved vs deployed; resize/release guards |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Shared Risk catalog and portfolio context on Simulation only; Backtest
disables portfolio context rather than forking Risk. Allocation authority stays
in Portfolio/accounting; Risk reads it. Settings remain defaults.

## Project Structure

### Documentation (this feature)

```text
specs/010-advanced-risk-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── risk-catalog.md
│   └── simulation-risk-api.md
└── tasks.md                 # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/app/simulation/control/risk.py          # EXTEND RiskContext + review order
backend/app/simulation/control/reasons.py       # NEW shared catalog (codes/messages)
backend/app/simulation/pipeline.py              # Pass portfolio context; stop on portfolio_max_loss
backend/app/simulation/session_service.py       # Create/start available check; persist effective risk
backend/app/portfolio/service.py                # Allocation resize/release while bound
backend/app/settings/service.py                 # Optional defaults for new risk fields
backend/app/backtest/engine.py                  # Same RiskManager; portfolio context off
backend/app/db/models.py                        # Session + defaults columns
backend/tests/unit/test_risk_*.py
backend/tests/contract/test_simulation_api.py
backend/tests/contract/test_portfolio_api.py
frontend/src/features/simulation/               # Optional bind + portfolio risk fields
frontend/src/features/settings/                 # Optional defaults
frontend/src/__tests__/                         # Simulation/settings risk UI
```

**Structure Decision**: Extend existing Simulation Risk and Portfolio packages.
No `app.risk_engine` fork. Catalog module shared by Simulation, Backtest, and
journals.

## Complexity Tracking

> Dual session cash vs Portfolio USDT remains an explicit 010 assumption (not a
> second Risk engine). Portfolio gates are Simulation-context fields on
> `RiskContext`, disabled for Backtest/Comparison.
