# Quickstart: Simulation Portfolio

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Contracts**: [contracts/portfolio-api.md](./contracts/portfolio-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate Simulation Portfolio: fund USDT, fill-driven holdings, valuation,
compact capital reservation, persistence — without XT private APIs and
without a manual crypto-entry form.

## Prerequisites

- Features 001–008 available
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

pytest tests/contract/test_simulation_api.py \
       tests/contract/test_backtest_api.py -q

cd ../frontend && npm test -- --run src/__tests__/portfolio
```

Expected:

- Funding sets USDT / `cash`; `available = cash − reserved`
- `PUT /portfolio/holdings` is not a valid operator API (404/405)
- Simulated BUY/SELL apply updates USDT and the traded asset when USDT can
  absorb the cash effect
- Refused apply leaves Feature 003 journals intact and sets GET `warning`
- `deployed` / `positions` reflect an active Simulation long when present
- Equity = sum of valued holdings; partial/stale labeled; USDT has no
  artificial unrealized P&L
- Over-reserve and under-reserved cash cuts return `400`
- `bookProvenance` is `simulation`
- Mutations persist a snapshot; GET does not
- Simulation/Backtest regression suites stay green
- UI has no BTC quantity entry form; Simulation is obvious

## Manual smoke

### 1) Fund simulation USDT

Open **Portfolio**. Confirm Simulation mode. Fund `1000` USDT. Holdings show
USDT only. Total value 1000. Available 1000.

### 2) No manual crypto entry

Confirm there is no control to type BTC/ETH/SOL quantity.

### 3) Simulated BUY then SELL

With Portfolio USDT funded to cover the fill, run (or test-apply) a simulated
BUY BTC that spends 200 USDT. Portfolio USDT decreases; BTC appears. While the
session is long, Capital shows non-zero Deployed. SELL reduces BTC, increases
USDT, updates realized P&L, Deployed returns to 0.

If Portfolio USDT cannot absorb the fill, session journals still record it and
Portfolio shows a warning; holdings do not go negative.

### 4) Compact allocations

Create two allocations summing to ≤ available USDT. Overspend rejected.
Holdings quantities unchanged. Allocation UI is not the page center.

### 5) Persistence

Reload → same quantities and reservations. No value-over-time chart.

### 6) Narrow layout

At ~375px, summary, holdings (cards if needed), and fund still work.

## Done when

- [ ] Automated portfolio unit + contract tests pass (fill apply; no public
      holdings upsert)
- [ ] Simulation/Backtest regression contracts pass
- [ ] Smoke steps observed
- [ ] No credentials / real-money / strategy balance-mutation paths
- [ ] No 009 history charts; current-state weight visual only
