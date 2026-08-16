# Contract: Real blocked recovery

**Feature**: `015-controlled-real-execution`  
**Date**: 2026-08-16  
**Kind**: Startup / in-session / resume behavioral contract  
**Related**: Feature 014 Simulation recovery (unchanged for `mode=simulation`)

---

## Principle

For `mode=real`, **never** auto-resume trading after process death. Do **not**
extend Feature 014 conditional auto-recovery into Real for this MVP.

Use shared `RECOVERY_BLOCKED` with **dedicated Real behavior** (also for
in-session partial fill and unsettled timeout — FR-006b / FR-006c).

---

## Startup (orphan Real session)

If a Real session is found in `RUNNING` or `STOPPING` (or equivalent active
Real trading occupation) at backend start:

1. Transition to `RECOVERY_BLOCKED`.
2. Discard all `pending` entry confirmations (`cancelled` / recovery reason).
3. Reconcile XT balances / open orders / **retained** order ids vs local
   session via Feature 013 (do not drop known `xt_order_id`s).
4. Leave session non-trading (`allows_strategy_execution == false`).
5. Surface `recoveryReason` / detail for operator UI.

Simulation orphans continue to use Feature 014 recover-and-reconcile rules
(including conditional auto-resume when gates pass).

---

## In-session block (partial / unsettled)

| Trigger | Exposure | State | New orders / strategy |
|---------|----------|-------|------------------------|
| Partial XT fill (FR-006b) | Record actual filled qty/price | `RECOVERY_BLOCKED` | Forbidden until Resume/Stop |
| Poll timeout / unclear with known or possible order (FR-006c) | Do not invent fill; retain `xt_order_id` when known | `RECOVERY_BLOCKED` / unsettled | Forbidden until later reconcile settles outcome |

---

## Operator Resume (Real)

`POST .../resume` on Real `RECOVERY_BLOCKED`:

| Gate | Required |
|------|----------|
| Reconcile complete and non-contradictory (incl. retained orders) | Yes |
| Safety / risk re-check (mark, flatten flags, caps, XT free if entering) | Yes |
| Pending confirmations | Must be absent on restart path; none while unsettled |
| No outstanding unsettled order blocking new trading | Yes |

If any gate fails → remain `RECOVERY_BLOCKED`; code `resume_unavailable`.

On success → `RUNNING` (explicit only).

---

## Operator Stop / Flatten (Real)

From `RECOVERY_BLOCKED` or `RUNNING`: Stop/Flatten MUST NOT wait for entry
confirmation. Flatten uses RealExecutionAdapter market SELL only when
reconcile proves a trustworthy open position / executable path; otherwise fail
closed / unsafe flatten status (existing patterns). Partial exposure still
counts as real risk to flatten when XT confirms base qty.

---

## Tests (required)

- Simulated restart leaves Real blocked (no strategy orders).
- Partial fill records exposure and blocks strategy trading.
- Timeout retains order id when known; blocks new orders; later reconcile
  settles before Resume.
- Resume blocked when reconcile incomplete.
- Resume after safe reconcile succeeds.
- Pending confirm discarded on recovery entry (restart).
- Simulation auto-recovery behavior unchanged in fixture that proves mode
  branch.
