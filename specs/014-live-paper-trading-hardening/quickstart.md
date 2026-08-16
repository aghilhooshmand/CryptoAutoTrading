# Quickstart: Feature 014 — Live Paper-Trading Hardening

**Date**: 2026-08-16  
**Goal**: Validate restart recovery, reconciliation, `RECOVERY_BLOCKED`, offline
gap skip, and bounded public retries without enabling Real trading.

See also: [contracts/simulation-recovery-api.md](./contracts/simulation-recovery-api.md),
[contracts/public-market-retry.md](./contracts/public-market-retry.md),
[data-model.md](./data-model.md), [research.md](./research.md).

---

## Prerequisites

- Branch `014-live-paper-trading-hardening`
- Backend + frontend as for Features 003/009/010/011
- **No** XT private credentials required for paper-trading validation
- Prefer fixtures / mocks for market data and DB sessions in CI

---

## 1. Automated gates (preferred)

From `backend/`:

```bash
pytest -q \
  tests/unit/test_reconcile.py \
  tests/unit/test_recovery_014.py \
  tests/unit/test_gap_skip.py \
  tests/unit/test_public_market_retry.py \
  tests/unit/test_state_machine.py \
  tests/contract/test_simulation_resume_api.py
```

Expect:
- Reconcile pass → auto-resume path to `RUNNING` (startup fixture)
- Any failed gate → `RECOVERY_BLOCKED`, zero new fills
- Duplicate candle / watermark replay → zero second fills
- Offline gap skip → watermark advanced, audit recorded, no gap fills
- Public retry: one retry then fail; no invent; no duplicate trades
- `POST .../resume` from `RECOVERY_BLOCKED` re-checks gates
- `STOPPED` resume rejected (`invalid_state_for_resume`)
- Emergency stop from `RECOVERY_BLOCKED` / degraded RUNNING blocks entries
- RealExecutionAdapter still unavailable; no private trading calls

Frontend (once UI lands):

```bash
# from frontend/
npm test -- --run
```

Cover `RECOVERY_BLOCKED` status visibility and Resume control; ~375px layout
smoke if project has viewport tests.

---

## 2. Manual restart walkthrough (after implement)

1. Start backend + frontend; create and start a Simulation (flat or long).
2. Note `lastProcessedCandleOpenTime` and session id.
3. Kill backend process hard (SIGKILL) while `RUNNING`.
4. Restart backend.
5. Observe either:
   - Auto-resume `RUNNING` after reconcile + optional skipped-gap, **or**
   - `RECOVERY_BLOCKED` with visible `recoveryReason` (not normal `STOPPED`).
6. Confirm no fills invented for downtime candles.
7. If blocked: fix underlying mismatch in fixtures (or stop/close); use
   **Resume** only when gates can pass; or stop and start a **new** session.
8. Trigger emergency stop while market fetch is forced unsafe — confirm no new
   entries.

---

## 3. Safety checklist

- [ ] No invented prices / fills / Portfolio balances on recovery
- [ ] `RECOVERY_BLOCKED` ≠ History `STOPPED`
- [ ] Simulation Portfolio never merged with Real XT
- [ ] RealExecutionAdapter still unavailable
- [ ] Public retries bounded (≤1 retry, ≤2s Retry-After wait)
- [ ] Operator can distinguish blocked vs completed at ~375px width

---

## 4. Out of scope reminders

Do not validate XT place/cancel, Real trading mode, Torque, GE, or Backtest
redesign as part of Feature 014.
