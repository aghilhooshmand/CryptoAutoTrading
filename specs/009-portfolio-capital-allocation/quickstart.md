# Quickstart: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Contracts**: [contracts/portfolio-api.md](./contracts/portfolio-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate local portfolio funding, allocation reservations, capital identity
(`available = cash − reserved`), persistence, and Portfolio UI — without
starting Simulation/Backtest trading.

## Prerequisites

- Features 001–008 available (app shell, Portfolio route, SQLite)
- Backend and frontend per root README

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# second terminal
cd frontend && npm run dev
```

## Automated checks (preferred)

```bash
cd backend && source .venv/bin/activate

pytest tests/unit/test_portfolio_*.py \
       tests/contract/test_portfolio_api.py -q

# Regression: session/run accounting unchanged
pytest tests/contract/test_simulation_api.py \
       tests/contract/test_backtest_api.py -q

cd ../frontend && npm test -- --run src/__tests__/portfolio
```

Expected:

- Funding sets cash; `available` tracks `cash − reserved`
- Over-reserve and under-reserved cash cuts return `400` and leave prior state
- Deployed stays `0`; positions stay `[]`
- Reload returns the same portfolio/allocations
- Simulation/Backtest contract suites still green

## Manual smoke

### 1) Fund portfolio

Open **Portfolio**. Set cash to `1000` USDT via funding. Confirm equity/cash/
available show `1000`, reserved `0`, deployed `0`, positions empty.

### 2) Split allocations

Create allocation A: label + `250` (optional `targetRef` e.g. `rsi`).  
Create allocation B: `250` with the **same** `targetRef` allowed.  
Confirm reserved `500`, available `500`.

### 3) Reject overspend

Attempt allocation `600` more → rejected; state unchanged.

### 4) Reject unsafe cash cut

Try funding cash to `400` while reserved is `500` → rejected; reserved still
`500`.

### 5) Release / resize

Resize or release an allocation → available increases; totals reconcile.
Confirm before release.

### 6) Persistence

Reload the app → same cash and allocations.

### 7) Narrow layout

At ~375px, complete fund + allocate without hover-only controls; capital terms
have short help where needed.

### 8) No trading side effects

Funding/allocate/release does not start Simulation or Backtest runs.

## Done when

- [x] Automated portfolio unit + contract tests pass
- [x] Simulation/Backtest regression contracts pass
- [x] Smoke steps 1–8 observed
- [x] No credentials / real-money / strategy balance mutation paths introduced
