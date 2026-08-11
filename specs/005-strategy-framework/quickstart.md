# Quickstart: Strategy Framework and Selection

**Feature**: `005-strategy-framework`  
**Date**: 2026-08-11  
**Contracts**: [contracts/strategy-api.md](./contracts/strategy-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate that Dual EMA is selectable with editable defaults, that Simulation
and Backtest share one implementation, and that omit/alias/invalid cases fail
safely.

## Prerequisites

- Backend and frontend running per root README
- Feature 003 simulation and Feature 004 backtest already workable
- Public market data available for a short live sim smoke (or use fixtures in tests)

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm run dev
```

## Automated checks (preferred)

```bash
cd backend && source .venv/bin/activate
pytest tests/unit/test_strategy_registry.py \
       tests/unit/test_dual_ema_params.py \
       tests/unit/test_dual_ema_continuity.py \
       tests/contract/test_strategies_api.py -q

# Extended create contracts (after implementation updates existing files)
pytest tests/contract/test_simulation_api.py tests/contract/test_backtest_api.py -q -k strategy

cd ../frontend && npm test -- --run src/__tests__/strategyConfig.test.tsx
```

Expected: registry/alias/defaults/validation tests green; continuity fixture
matches pre-migration Dual EMA 9/21 signals; UI test covers selector + periods.

## Manual smoke

### 1) List strategies

```bash
curl -sS http://127.0.0.1:8000/strategies | jq .
```

Expect exactly one strategy with `"id": "dual_ema"`, defaults 9/21, and alias
`dual_ema_9_21` listed under `aliases` (not as a second strategy).

### 2) Reject omitted strategyId

```bash
curl -sS -o /tmp/out.json -w "%{http_code}" \
  -X POST http://127.0.0.1:8000/simulation/sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "mode":"simulation","symbol":"btc_usdt","timeframe":"1h",
    "startingCapital":"500","allocatedCapital":"500","maxPositionSize":"500",
    "targetNetProfitRate":"0.01","maxSessionLossRate":"0.007",
    "maxTrades":20,"durationSeconds":3600
  }'
```

Expect HTTP `400` and a clear missing/invalid strategy error (not a created
session).

### 3) Alias → canonical persist

Create a session or backtest with `"strategyId":"dual_ema_9_21"` and **no**
`strategyParams`. Expect success response with `"strategyId":"dual_ema"` and
`"strategyParams":{"fastPeriod":9,"slowPeriod":21}`.

### 4) Custom periods + insufficient history

Run a backtest with `strategyParams: {"fastPeriod":5,"slowPeriod":50}` and a
window that yields fewer than 50 closed candles. Expect `insufficient_history`
(failed run if post-accept) — not silent 9/21 behavior.

### 5) UI under Auto Trading

1. Open `/auto-trading` → Simulation tab: strategy selector shows Dual EMA;
   periods default 9/21 and are editable.
2. Switch to Backtest tab: same strategy fields; run with defaults; results
   show strategy id + params.
3. Confirm no fourth primary nav item.

### 6) Continuity (default 9/21)

With Dual EMA defaults, a known fixture (or short documented window) should
match prior Dual EMA 9/21 signal/trade behavior used before Feature 005
(automated continuity test is the source of truth).

## Pass criteria

- [ ] `GET /strategies` returns only `dual_ema` (+ alias metadata)
- [ ] Create without `strategyId` fails
- [ ] Alias create persists `dual_ema` + effective params
- [ ] Custom `slowPeriod` drives insufficient-history threshold
- [ ] Simulation and Backtest UIs share selectable Dual EMA params
- [ ] Continuity tests pass for defaults 9/21

## Out of scope for this quickstart

- Adding a second strategy
- Real-money mode
- Mid-session strategy change
