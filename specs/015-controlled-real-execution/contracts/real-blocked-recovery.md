# Contract: Real blocked recovery

**Feature**: `015-controlled-real-execution`  
**Date**: 2026-08-16  
**Kind**: Startup / resume behavioral contract  
**Related**: Feature 014 Simulation recovery (unchanged for `mode=simulation`)

---

## Principle

For `mode=real`, **never** auto-resume trading after process death. Do **not**
extend Feature 014 conditional auto-recovery into Real for this MVP.

---

## Startup (orphan Real session)

If a Real session is found in `RUNNING` or `STOPPING` (or equivalent active
Real trading occupation) at backend start:

1. Transition to `RECOVERY_BLOCKED`.
2. Discard all `pending` entry confirmations (`cancelled` / recovery reason).
3. Reconcile XT balances / open orders / known order ids vs local session via
   Feature 013.
4. Leave session non-trading (`allows_strategy_execution == false`).
5. Surface `recoveryReason` / detail for operator UI.

Simulation orphans continue to use Feature 014 recover-and-reconcile rules
(including conditional auto-resume when gates pass).

---

## Operator Resume (Real)

`POST .../resume` on Real `RECOVERY_BLOCKED`:

| Gate | Required |
|------|----------|
| Reconcile complete and non-contradictory | Yes |
| Safety / risk re-check (mark, flatten flags, caps) | Yes |
| Pending confirmations | Must be absent (already discarded) |

If any gate fails → remain `RECOVERY_BLOCKED`; code `resume_unavailable`.

On success → `RUNNING` (explicit only).

---

## Operator Stop / Flatten (Real)

From `RECOVERY_BLOCKED` or `RUNNING`: Stop/Flatten MUST NOT wait for entry
confirmation. Flatten uses RealExecutionAdapter market SELL only when
reconcile proves a trustworthy open position / executable path; otherwise fail
closed / unsafe flatten status (existing patterns).

---

## Tests (required)

- Simulated restart leaves Real blocked (no strategy orders).
- Resume blocked when reconcile incomplete.
- Resume after safe reconcile succeeds.
- Pending confirm discarded on recovery entry.
- Simulation auto-recovery behavior unchanged in fixture that proves mode
  branch.
