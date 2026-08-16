# Contract: Confirmation gate

**Feature**: `015-controlled-real-execution`  
**Date**: 2026-08-16  
**Kind**: Pipeline behavioral contract

---

## When the gate applies

| Intent | Mode | Gate |
|--------|------|------|
| Exposure-increasing BUY | `real` | **Required** after Controller+Risk APPROVE |
| TP/SL protective SELL | `real` | Skip |
| Strategy SELL reducing/closing long | `real` | Skip |
| Emergency / STOP flatten (safe path) | `real` | Skip |
| Any BUY/SELL | `simulation` | N/A (paper path unchanged) |

---

## Pipeline behavior (Real BUY)

```text
Strategy BUY
  → Controller APPROVE
  → Risk APPROVE
  → Execution: create PendingEntryConfirmation (TTL 5m)
  → DO NOT call RealExecutionAdapter
  → Status shows pendingConfirmation
```

Operator:

```text
confirm-entry
  → re-run safety / risk / capital cap / mark trust
  → if fail: reject pending; no XT
  → if pass: RealExecutionAdapter.place MARKET BUY
  → reconcile before local fill
```

or decline / expire / stop → discard; no XT.

---

## TTL

- Duration: **5 minutes** from pending creation.
- On expiry: status `expired`; no XT order; session remains `RUNNING`.
- Expired pending MUST NOT be confirmable.

---

## Concurrency

- At most one `pending` confirmation per Real session.
- While pending exists, do not enqueue a second BUY pending (fail closed /
  hold).

---

## Restart

Entering Real blocked recovery **discards** all pendings (see
[real-blocked-recovery.md](./real-blocked-recovery.md)).
