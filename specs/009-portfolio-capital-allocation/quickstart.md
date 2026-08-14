# Quickstart: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Contracts**: [contracts/portfolio-api.md](./contracts/portfolio-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate one-book holdings + quote-cash reservation: funding, local/manual
holdings, valuation (including partial/stale), allocations, persistence, and
Portfolio UI — without starting Simulation/Backtest or calling XT private APIs.

## Prerequisites

- Features 001–008 available (app shell, Portfolio route, public market data,
  SQLite)
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

- Funding sets USDT holding / `cash`; `available = cash − reserved`
- Local BTC (or other supported) holding appears with provenance `local_manual`
- Equity = sum of valued holdings; `equityComplete` false when a holding has
  no price; stale last-known still included with stale status
- Over-reserve and under-reserved cash cuts return `400` and leave prior state
- Holdings upsert of `usdt` rejected (funding only)
- Deployed stays `0`; positions stay `[]`
- Mutations persist a historical snapshot; GET does not
- Reload returns the same quantities and reservations (prices may refresh)
- Simulation/Backtest contract suites still green

## Manual smoke

### 1) Fund quote cash

Open **Portfolio**. Set cash to `1000` USDT. Confirm USDT holding quantity
`1000`, available `1000`, reserved `0`, deployed `0`, positions empty.
Provenance is local/manual, not a live exchange account.

### 2) Record a local holding

Add BTC quantity `0.005` with optional average cost. Confirm holdings table
shows quantity, public price or unavailable/stale, value when known, and
weight vs USDT. Equity is the sum of valued lines; if BTC is unvalued, equity
is labeled partial.

### 3) Split allocations

Create allocation A: `250` (optional `targetRef` `rsi`).  
Create allocation B: `250` with the **same** `targetRef`.  
Confirm reserved `500`, available `500`. BTC quantity unchanged.

### 4) Reject overspend and unsafe cash cut

Allocate more than available → rejected.  
Fund cash to below reserved → rejected; holdings/reservations unchanged.

### 5) Release / resize / remove holding

Resize or release an allocation (confirm release). Remove BTC (confirm).
Totals reconcile.

### 6) Persistence

Reload → same USDT quantity, remaining holdings, and allocations. No
value-over-time chart.

### 7) Narrow layout

At ~375px, fund, record a holding, and allocate without hover-only controls.

### 8) No trading side effects

None of the above starts Simulation or Backtest or requires XT credentials.

## Done when

- [ ] Automated portfolio unit + contract tests pass (including holdings and
      partial equity)
- [ ] Simulation/Backtest regression contracts pass
- [ ] Smoke steps 1–8 observed
- [ ] No credentials / real-money / strategy balance mutation paths introduced
- [ ] No 009 UI charts for drawdown or value-over-time
