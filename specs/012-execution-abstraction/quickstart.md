# Quickstart: Execution Abstraction

**Feature**: `012-execution-abstraction`  
**Date**: 2026-08-15  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/execution-contract.md](./contracts/execution-contract.md) · **Call sites**: [call-sites.md](./call-sites.md)

Validation guide for implementers and reviewers. Behavior-preserving backend
refactor — no new operator UI.

---

## Prerequisites

- Branch `012-execution-abstraction`
- Backend test env as for Features 003/004 (pytest)
- No schema migrate step for this feature

---

## Setup

```bash
cd backend
# use project venv / deps as usual (see README)
```

---

## Automated checks (preferred)

```bash
cd backend

# New contract / unit focus
python -m pytest \
  tests/unit/test_execution_economics.py \
  tests/unit/test_real_execution_stub.py \
  -q

# Behavior gates (must stay green with unchanged expectations)
python -m pytest \
  tests/unit/test_backtest_fills.py \
  tests/unit/test_forced_close.py \
  tests/unit/test_accounting.py \
  tests/unit/test_risk_rejects.py \
  -q

# Broader Simulation / Backtest / Portfolio fill-apply suites used by the project
# (adjust to exact filenames present on branch — include pipeline + portfolio apply)
python -m pytest tests/unit/test_backtest_pipeline.py tests/contract/ -q --tb=no
```

Expected:

- Shared economics produce the same reject codes and fill quotes as pre-012
  for identical intents.
- Real stub returns `ok=false`, `reason_code=real_execution_unavailable`, and
  tests assert no Portfolio/ledger mutation helpers were invoked.
- Backtest next-open and missing-next-candle (`approved_unexecutable`) behavior
  unchanged.
- Simulation forced-close / unsafe-unflattened behavior unchanged.

---

## Manual / review scenarios

### 1. Single contract visible

1. Open `app/execution/` (or documented public exports).
2. Confirm Historical, Simulation, and Real adapters implement
   `ExecutionEngine.execute`.
3. Confirm production Simulation pipeline and Backtest engine strategy fills
   call through that contract (see [call-sites.md](./call-sites.md)) — wrappers
   must call `execute`, not shared helpers alone.
4. Confirm legacy shims under `simulation/execution/` and `backtest/execution.py`
   are re-export-only (no local fill bodies).

### 2. Mode policies still split

1. Trace Backtest strategy fill → `reference_price` is next candle open.
2. Trace Simulation strategy fill → `reference_price` is live/safe mark path.
3. Confirm Portfolio apply remains only on Simulation success path.
4. Confirm Backtest/Comparison path never imports Portfolio fill-apply for
   historical fills.

### 3. Real not operator-selectable

1. Inspect Simulation/Backtest create UI and session/run APIs.
2. Confirm no Real execution mode option was added.
3. Invoke Real adapter only from unit test; observe structured failure.

### 4. Comparison still shares Historical

1. Confirm Comparison still runs legs via Backtest
   `run_leg_with_prefetched_candles` → `run_engine` (see [call-sites.md](./call-sites.md)).
2. Confirm that engine uses the shared Historical adapter (same module after
   refactor).

---

## Done when

- [ ] Spec locks FR-001–FR-017 satisfied
- [ ] Contract [execution-contract.md](./contracts/execution-contract.md) met
- [ ] Regression gates green without intentional expectation edits
- [ ] Real stub tested for `real_execution_unavailable` + no state mutation
- [ ] ROADMAP Feature 012 can move to DONE after `/speckit-tasks` + implement
