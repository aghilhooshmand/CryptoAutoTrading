# Quickstart: Additional Strategies

**Feature**: `006-additional-strategies`  
**Date**: 2026-08-12  
**Contracts**: [contracts/additional-strategies-api.md](./contracts/additional-strategies-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate that RSI, MACD, Bollinger Bands, and Breakout are selectable in
Simulation and Backtest, share registry implementations, keep Dual EMA
unchanged, and honor recovery-crossover / every-new-extreme / `S`/`S+1` rules.

## Prerequisites

- Feature 005 strategy framework working (`GET /strategies`, Dual EMA create)
- Backend and frontend per root README

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

# Dual EMA must still pass unmodified
pytest tests/unit/test_dual_ema_continuity.py -q

# New strategy unit / golden tests (paths as implemented)
pytest tests/unit/test_rsi_strategy.py \
       tests/unit/test_macd_strategy.py \
       tests/unit/test_bollinger_strategy.py \
       tests/unit/test_breakout_strategy.py -q

# Catalog
pytest tests/contract/test_strategies_api.py -q

# Create + insufficient history for a new strategy
pytest tests/contract/test_simulation_api.py \
       tests/contract/test_backtest_api.py -q -k "rsi or macd or bollinger or breakout or strateg"

cd ../frontend && npm test -- --run src/__tests__/strategyConfig.test.tsx
```

Expected: five strategies listed; golden sequences match documented algorithms;
Dual EMA continuity green; invalid params rejected with constraint messages.

## Manual smoke

### 1) List strategies

```bash
curl -sS http://127.0.0.1:8000/strategies | jq '.strategies | map({id, displayName})'
```

Expect five ids: `dual_ema`, `rsi`, `macd`, `bollinger_bands`, `breakout`.

### 2) Reject invalid RSI params

Create a simulation (with otherwise valid Feature 003 body) using:

```json
"strategyId": "rsi",
"strategyParams": { "period": 14, "overbought": 30, "oversold": 70 }
```

Expect `400` and message about oversold &lt; overbought.

### 3) Create with each new strategy (defaults)

From Auto Trading UI (or curl): create one simulation and one short backtest
per strategy id with defaults. Confirm inspect surfaces show canonical id and
effective params.

### 4) Dual EMA regression

Create Dual EMA 9/21 session/backtest; confirm behavior and listing still
include Dual EMA unchanged.

### 5) Insufficient history

Run a backtest for Breakout with lookback 20 on a window with fewer than 20
closed candles → `insufficient_history`. With exactly 20 candles → run
accepted; early bars HOLD until crossover-ready (`S+1`).

## Done when

- [ ] `GET /strategies` returns 5 strategies with correct schemas
- [ ] All four new strategies runnable on Simulation and Backtest
- [ ] Dual EMA continuity tests pass without modification
- [ ] Golden unit tests lock signal semantics (RSI/Bollinger recovery;
      MACD crossover; Breakout every new extreme)
- [ ] UI selector shows all strategies; params render dynamically including
      Bollinger `stdDev`
