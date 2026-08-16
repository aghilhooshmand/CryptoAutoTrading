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
  tests/unit/test_protective_exits.py \
  tests/unit/test_strategy_ohlc_025.py \
  tests/unit/test_stochastic.py \
  tests/unit/test_keltner.py \
  tests/unit/test_roc_momentum.py \
  tests/integration/test_simulation_pipeline.py \
  tests/integration/test_backtest_protective_exits.py
```

(Adjust paths to match final test filenames from `/speckit-tasks`.)

Expect:

- TP and SL trigger on high/low after entry bar
- SL wins when both touch
- No fill at TP/SL level
- Repeated BUY/exit cycles keep cash/holdings consistent
- New strategies registered and deterministic
- Existing five strategies unchanged on close-only behavior

Frontend (once UI lands):

```bash
# from frontend/
npm test -- --run
```

Cover TP%/SL% on create forms and absolute levels on status (~375px smoke if
present).

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

After implement, run end-to-end:

```text
Backtest → config → Simulation → BUY → position
→ TP or SL or strategy EXIT → cash/holdings/P&L → history
→ stop / restart (014 as-is)
```

Open defects only if concrete failures appear.

---

## 5. Out of scope reminders

Do not validate Real XT orders, Torque, GE, trailing stops, volume strategy, or
Portfolio redesign as part of Feature 025.
