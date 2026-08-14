# Quickstart: Advanced Risk Management

**Feature**: `010-advanced-risk-management`  
**Date**: 2026-08-14  
**Contracts**: [contracts/risk-catalog.md](./contracts/risk-catalog.md),
[contracts/simulation-risk-api.md](./contracts/simulation-risk-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate portfolio-aware Simulation Risk without XT private APIs and without a
second risk engine.

## Prerequisites

- Features 001–009 available
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

pytest tests/unit/test_risk_*.py \
       tests/unit/test_max_trades.py \
       tests/unit/test_risk_rejects.py -q

pytest tests/contract/test_simulation_api.py \
       tests/contract/test_portfolio_api.py \
       tests/contract/test_backtest_api.py -q

cd ../frontend && npm test -- --run src/__tests__/
```

Expected:

- Create/start rejected when `allocatedCapital >` Portfolio available
- Bound BUY rejected when notional > allocation remaining; unbound BUY does
  not re-check available
- Allocation release/resize blocked while bound (resize only if ≥ deployed)
- Portfolio max-loss: frozen baseline; stop when computable loss ≥ bound;
  uncomputable → BUY reject, no invented stop
- Per-symbol cap: projected post-BUY weight; fail closed if incomplete
- Journals show first failing catalog `reasonCode` + separate message
- Settings defaults copy at create; later Settings edits leave session frozen
- Backtest regression green (no live Portfolio gates)

## Manual smoke

### 1) Available at create

Fund Portfolio `1000` USDT. Create allocation reserved `400`. Try Simulation
with `allocatedCapital` `700` → rejected (`insufficient_portfolio_available`).
Use `600` → accepted.

### 2) Bound allocation BUY

Bind session to the `400` allocation. After a long that deploys most of the
sleeve, further BUY that would exceed remaining → rejected
(`allocation_exposure_exceeded`). Attempt release of that allocation → blocked.

### 3) Portfolio max-loss

Configure a small portfolio max-loss, start session, drive known-value loss to
the bound → session stops with `portfolio_max_loss`. With incomplete equity
under an equity baseline → BUYs blocked with
`portfolio_max_loss_uncomputable` (no invented stop).

### 4) Per-symbol cap

Set `perSymbolMaxWeight` to a low value; attempt BUY that would breach →
`per_symbol_exposure_exceeded`. Missing price → fail closed.

### 5) Settings defaults-only

Save portfolio risk defaults in Settings. Create a session (fields prefilled).
Change Settings. Reopen the session → effective risk fields unchanged.

### 6) Backtest unchanged for portfolio gates

Run a Backtest with optional session loss/max trades only. Confirm no Portfolio
available / allocation binding requirements.

## Out of scope checks

- No daily loss / timezone reset UI
- No drawdown **stop**
- No real-money / XT private
- No second Risk package for Backtest
