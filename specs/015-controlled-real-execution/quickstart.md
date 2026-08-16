# Quickstart: Feature 015 — Controlled Real Execution

**Date**: 2026-08-16  
**Goal**: Validate Controlled Real confirmation, market-only execution,
Portfolio isolation, and blocked recovery **without requiring live XT** in
the default path.

See: [session-real-api.md](./contracts/session-real-api.md),
[confirmation-gate.md](./contracts/confirmation-gate.md),
[real-execution-adapter.md](./contracts/real-execution-adapter.md),
[real-blocked-recovery.md](./contracts/real-blocked-recovery.md),
[data-model.md](./data-model.md).

---

## Prerequisites

- Branch `015-controlled-real-execution`
- Backend + frontend as for Features 003–014/025
- Default validation: **fakes/mocks** for XT place + get order
- Optional live smoke: `XT_API_KEY` / `XT_API_SECRET` + tiny ≤ 50 USDT only

---

## 1. Automated gates (preferred)

From `backend/` (exact module names may match tasks.md once generated):

```bash
pytest -q \
  tests/unit/test_real_confirmation_gate.py \
  tests/unit/test_real_pending_ttl.py \
  tests/unit/test_real_execution_adapter.py \
  tests/unit/test_real_blocked_recovery.py \
  tests/unit/test_real_portfolio_isolation.py \
  tests/contract/test_simulation_api.py \
  tests/contract/test_real_session_api.py
```

Expect:

- Risk-approved Real BUY does not call place until confirm
- Pending older than 5 minutes expires with no XT order; session stays running
- Confirm-time validation failure places no order
- Protective / reducing exits skip confirmation
- `allocatedCapital > 50` rejected; cap re-checked pre-submit
- Place ack alone does not create a local fill
- Limit order path rejected
- Real fills do not mutate Simulation Portfolio holdings
- Restart → Real `RECOVERY_BLOCKED`; no auto-resume; Resume gated

Frontend:

```bash
# from frontend/
npm test -- --run src/__tests__/controlledRealUi015.test.tsx
```

Cover Real mode label, pending confirm actions, blocked banner (~375px smoke).

---

## 2. Manual mocked walkthrough

1. Start backend/frontend with XT client faked or credentials unset for
   create-only checks.
2. Create session `mode=real`, allocated `10`, max position `10`.
3. Drive / wait until status shows `pendingConfirmation`.
4. Confirm → fake XT filled → status shows long from reconcile evidence.
5. Trigger TP/SL or strategy exit → no confirm prompt; position flattens after
   reconcile.
6. Create with allocated `51` → rejected.
7. Simulate restart mid-Real → UI shows blocked; Resume disabled until fake
   reconcile passes; then Resume or Stop.

---

## 3. Optional live smoke (gated)

Only with real credentials and **≤ 50 USDT** allocated:

1. Create Real session on a liquid pair with tiny notional.
2. Confirm one BUY; verify XT open/history matches local reconcile.
3. Stop/flatten; verify no leftover assumed position.
4. Do **not** run autonomy or limit orders.

Abort immediately on any local/XT mismatch.

---

## 4. MVP-2 acceptance pointer

Roadmap Controlled Real MVP is satisfied when SC-001–SC-008 (spec) pass under
this quickstart’s automated gates (live smoke optional).
