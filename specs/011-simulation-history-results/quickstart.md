# Quickstart: Simulation History & Results

**Feature**: `011-simulation-history-results`  
**Date**: 2026-08-15  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/simulation-history-api.md](./contracts/simulation-history-api.md)

Validation guide for implementers and reviewers. Not an implementation dump.

---

## Prerequisites

- Backend + frontend runnable as for Feature 003/010.
- Feature 002 public market data available for **live** Simulation runs (not
  for backfill).
- Optional: Feature 009 Portfolio with an allocation for binding delete tests.

---

## Setup

```bash
# From repo root — use project’s usual backend/frontend start (see README)
# Ensure branch 011-simulation-history-results and migrations/column ensure applied
```

---

## Automated checks (preferred)

```bash
# Backend — adjust paths to match tasks.md once written
pytest backend/tests/unit/test_simulation_final_result.py -q
pytest backend/tests/contract/test_simulation_history_api.py -q

# Frontend
# npm/vitest targets for simulationHistory* once added
```

Expected: freeze completeness, ledger-only backfill, list/filter, delete
guards, immutability of frozen metrics after mark change, Portfolio balances
unchanged on delete.

---

## Manual / API scenarios

### 1. List and open History

1. Create/start several Simulations; stop at least two; leave zero or one RUNNING.
2. `GET /simulation/sessions` → all appear; states distinguishable.
3. `GET /simulation/sessions?state=STOPPED` → only STOPPED.
4. Open detail route from Simulation tab History list → config (incl.
   `decisionLogMode`), trades, decisions (persisted only; Risk rejects if any),
   timestamps, stop reason visible. No fabricated HOLDs.
5. STOPPED detail at `/auto-trading/simulation/:sessionId` shows **no** restart / resume / run-again control; CONFIGURED may Start via existing Feature 003 path.
6. List pagination: with `totalCount` > `limit`, request `offset=limit` and receive older sessions (order `created_at DESC, id DESC`).

### 2. Frozen results do not drift

1. Run a Simulation to STOPPED with flat (or complete) freeze; note
   `finalResult.netPnl` / `endingEquity`.
2. Change market prices (or mock quotes) so live marks would differ.
3. `GET /simulation/sessions/{id}` again → `finalResult` metrics unchanged.

### 3. Incomplete freeze

1. Force a path that stops long without safe mark (`unsafe_unflattened` if
   reproducible) **or** inspect a backfilled long legacy session.
2. `finalResult.complete === false`; `endingEquity` / `netPnl` / `returnPct`
   are null; fees/cash/flatten/stopReason still present.

### 4. Pre-011 / missing freeze backfill

1. Insert or use a STOPPED session with `final_result_json` null (test fixture).
2. List or get session → snapshot appears; if flat, complete from cash; if long,
   incomplete — **no** quote API call required for backfill.

### 5. Delete rules

1. `DELETE` while RUNNING → `409` `session_active`.
2. CONFIGURED/STOPPED with allocation still reserved/deployed for binding →
   `409` `portfolio_binding_active`; Portfolio totals unchanged.
3. After binding cleared / STOPPED eligible → confirm in UI → `204`; session
   gone from list; journals gone; Portfolio balances unchanged.

### 6. Refresh does not stop

1. Start RUNNING session.
2. Browser refresh / leave Auto Trading and return.
3. Session still RUNNING; reconnect via active endpoint / History; no stop
   solely from remount.

### 7. Responsive smoke

1. ~375px width: History list → detail → delete confirm/cancel reachable.

---

### 8. No resume / restart / worker recreation

1. After backend restart recovery marks a session STOPPED, confirm it is
   inspectable with freeze/backfill and there is no API/UI to resume that
   session id or recreate its worker.
2. STOPPED History detail offers no restart control.

---

## Done when

- Contract behaviors above pass in automated tests where practical.
- Spec success criteria SC-001–SC-006 are demonstrable.
- Constitution: no second accounting engine; no Portfolio unwind on delete;
  frozen metrics immutable to later prices.
