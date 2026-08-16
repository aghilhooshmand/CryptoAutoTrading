# Quickstart: Feature 025 — Stage-1 Trading Gap-Close

**Date**: 2026-08-16  
**Goal**: Validate per-position TP/SL, OHLC strategies, and intentional
Sim/Backtest semantics without Real trading.

See: [protective-exits.md](./contracts/protective-exits.md),
[strategy-ohlc-and-additions.md](./contracts/strategy-ohlc-and-additions.md),
[sim-vs-backtest-semantics.md](./contracts/sim-vs-backtest-semantics.md),
[data-model.md](./data-model.md).

---

## Prerequisites

- Branch `025-stage1-trading-gap-close`
- Backend + frontend as for Features 003–014
- **No** XT private credentials required

---

## 1. Automated gates (preferred)

From `backend/`:

```bash
pytest -q \
  tests/unit/test_tpsl.py \
  tests/unit/test_protective_exits_simulation.py \
  tests/unit/test_protective_exits_backtest.py \
  tests/unit/test_protective_exit_precedence.py \
  tests/unit/test_sim_backtest_tpsl_parity.py \
  tests/unit/test_stochastic.py \
  tests/unit/test_keltner.py \
  tests/unit/test_roc_momentum.py \
  tests/contract/test_strategies_api.py \
  tests/contract/test_simulation_api.py \
  tests/unit/test_real_execution_stub.py
```

Expect:

- TP and SL trigger on high/low after entry bar
- SL wins when both touch
- No fill at TP/SL level
- Protective exits do not increment `strategyFillCount`
- New strategies registered (`stochastic`, `keltner_channel`, `roc_momentum`); no volume strategy
- Existing five strategies unchanged on close-only behavior

Frontend:

```bash
# from frontend/
npm test -- --run src/__tests__/tpslUi025.test.tsx
```

Cover TP%/SL% on create forms and absolute levels on status (~375px smoke).

---

## 2. Manual Backtest walkthrough

1. Create Backtest with strategy + `takeProfitPercent` / `stopLossPercent`.
2. Run until at least one long opens and later exits via TP or SL.
3. Confirm exit reason and that fill price follows next-open (not TP/SL level).
4. Repeat for strategy SELL with TP/SL configured but not hit.

---

## 3. Manual Simulation walkthrough

1. Create Simulation with TP%/SL%; start.
2. After a BUY, UI shows entry + derived absolute TP/SL.
3. When a later closed candle triggers, position closes with correct reason;
   session can trade again (cycles).
4. Confirm no mid-position TP/SL editor.

---

## 4. MVP-1 acceptance gate (not a feature)

After Feature 025 implementation is green:

1. Backtest → Simulation → BUY → TP/SL or strategy EXIT → accounting → history
2. Feature 014 restart recovery still works as-is (no expansion)
3. File only concrete defect follow-ups; do not expand scope into Real/Torque/GE

---

## Out of scope reminders

- No Real XT private trading
- No Feature 014 recovery redesign
- No Portfolio UX redesign
- No volume strategy / ticks / trailing stops
