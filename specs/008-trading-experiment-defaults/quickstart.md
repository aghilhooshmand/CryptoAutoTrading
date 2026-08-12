# Quickstart: Trading & Experiment Defaults

**Feature**: `008-trading-experiment-defaults`  
**Date**: 2026-08-12  
**Contracts**: [contracts/operator-defaults-api.md](./contracts/operator-defaults-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate local Settings: explicit Save/Reset, create-form prefill (fresh open
only), comparison first-leg seeding, and no rewrite of historical effective
configs.

## Prerequisites

- Features 003–007 available (Simulation, Backtest, Comparison, `/strategies`)
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

# Settings unit + contract (paths as implemented)
pytest tests/unit/test_settings_*.py \
       tests/contract/test_settings_api.py -q

# Existing create APIs still green (no accidental coupling)
pytest tests/contract/test_simulation_api.py \
       tests/contract/test_backtest_api.py \
       tests/contract/test_comparison_api.py -q

cd ../frontend && npm test -- --run src/__tests__/settings
```

Expected:

- `GET /settings` returns starters when empty
- `PUT` rejects bad capital nesting / bad strategy params; last good retained
- `POST /settings/reset` restores starters without creating sessions/runs
- Frontend: Settings tab under Auto Trading; Save required; forms prefill from
  saved Settings; draft not overwritten mid-edit

## Manual smoke

### 1) Save distinctive Settings

Open Auto Trading → **Settings**. Set symbol/timeframe, capital nesting,
costs, preferred strategy (e.g. `rsi` with valid params), leave optional risk
empty. **Save**. Leave and return → values persist.

### 2) Prefill create forms

Open fresh Simulation, Backtest, and Comparison forms.

Expect:

- Shared fields match saved Settings
- Simulation optional risk fields empty when unset in Settings; create still
  requires Simulation’s own rates before start
- Comparison **first leg** = preferred strategy/params; second leg = product
  starter (not a forced copy of preferred)

### 3) Unsaved draft isolation

Edit Settings without Save. Open a fresh create form → still last **saved**
values. Return to Settings → draft may still show unsaved edits until reload
policy implemented (saved active defaults unchanged).

### 4) Fresh-open only

Open Simulation, edit a field, switch tabs briefly without discarding → draft
values remain (not reset from Settings).

### 5) History immunity

Create a Backtest (or Simulation) with known fee/capital. Change Settings fee
and capital; Save. Reopen the historical run/session → original effective
config unchanged.

### 6) Validation and Reset

In Settings, break capital nesting → Save rejected with clear message; prior
saved Settings still used by forms. Confirm Reset → starters restored; no new
session/run/comparison created.

### 7) Narrow layout

At ~375px width, complete view → edit → Save without hover-only controls.

## Done when

- [x] Automated settings tests pass
- [x] Smoke steps 1–7 observed (API + UI automated coverage; manual UI pass recommended)
- [x] No Settings path starts/stops trading or requires exchange credentials
