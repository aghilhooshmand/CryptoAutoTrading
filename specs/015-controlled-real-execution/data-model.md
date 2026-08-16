# Data Model: Feature 015 — Controlled Real Execution

**Date**: 2026-08-16  
**Branch**: `015-controlled-real-execution`

---

## 1. Session (`mode`)

Extend existing `SimulationSessionRow` (same table / lifecycle).

| Field | Type | Rules |
|-------|------|-------|
| `mode` | string | `simulation` (default) \| `real` |
| Real create capital | decimal strings | `allocated_capital ≤ 50`; `0 < max_position_size ≤ allocated_capital` |
| Position | existing | At most one open **long** for the session |

**Real-specific rules:**

- Create with `mode=real` is allowed when credentials/config gates pass (or
  deferred until start — prefer fail at create if credentials missing for
  operator clarity).
- Real create **MUST NOT** call Simulation Portfolio reserve / bind that
  mutates Sim holdings (no `allocation_id` Portfolio write path for Real MVP).
- Simulation create behavior unchanged.

**Operator-visible provenance:** status/history always include `mode` and,
for Real, never imply `simulation` portfolio provenance.

---

## 2. PendingEntryConfirmation

Represents an approved exposure-increasing BUY awaiting operator action.

| Field | Type | Rules |
|-------|------|-------|
| `id` | UUID string | Primary key |
| `session_id` | UUID string | FK to session; at most **one** non-terminal pending per session |
| `symbol` | string | Must match session symbol |
| `side` | string | `BUY` only for MVP |
| `proposed_notional` / sizing fields | decimal strings | Bounded by cash, maxPositionSize, 50 USDT cap |
| `reference_price` | decimal string | Mark/ref used at Risk approval (informational) |
| `created_at` | datetime | TTL clock start |
| `expires_at` | datetime | `created_at + 5 minutes` |
| `status` | string | `pending` \| `confirmed` \| `declined` \| `expired` \| `cancelled` \| `rejected` |
| `decision_journal_ref` | optional | Link to Controller/Risk approval event |

**Transitions:**

```text
(none) → pending          Risk-approved Real BUY reaches Execution gate
pending → confirmed       Operator confirm + final validation + XT submit path started
pending → declined        Operator decline
pending → expired         TTL elapsed (no XT order)
pending → cancelled       Session stop / restart recovery discard
pending → rejected        Final pre-submit validation failed (no XT order)
```

Terminal statuses are immutable. Expired/declined/cancelled/rejected intents
MUST NOT be reused; a new entry requires a fresh Strategy → Controller → Risk
cycle.

**Persistence options (implementation may choose one):**
- Dedicated table `pending_entry_confirmations`, or
- Nullable columns on `SimulationSessionRow` for the single active pending.

Dedicated table preferred for audit clarity.

---

## 3. Real order reconcile view (local)

Tracks XT submission and reconcile without inventing fills.

| Field | Type | Rules |
|-------|------|-------|
| `session_id` | UUID | |
| `client_intent_id` | string | Local idempotency / journal link |
| `xt_order_id` | string \| null | Set when XT accepts place |
| `side` | `BUY` \| `SELL` | |
| `order_type` | `MARKET` | Only MARKET in MVP |
| `submit_status` | string | `not_submitted` \| `submitted` \| `submit_failed` |
| `reconcile_status` | string | `unsettled` \| `filled` \| `rejected` \| `unknown_fail_closed` |
| `filled_qty` / `avg_price` / `fee` | decimal strings \| null | **Only** from XT reconcile |
| `updated_at` | datetime | |

**Invariant:** Session `position_*` / cash for Real update **only** when
`reconcile_status=filled` (or defined partial rule — MVP prefers wait for
full fill or fail closed).

---

## 4. Session status additions (API)

| Field | Meaning |
|-------|---------|
| `mode` | `real` \| `simulation` |
| `pendingConfirmation` | null or summary (id, expiresAt, symbol, sizing) |
| `realReconcile` | optional summary (unsettled order present?) |
| `recoveryReason` / blocked flags | Real blocked recovery messaging |

---

## 5. State machine notes

| State | Simulation (014) | Real (015) |
|-------|------------------|------------|
| `RUNNING` | Normal; may auto-recover into it | Normal; may hold pending confirm |
| `RECOVERY_BLOCKED` | Resume after gates; startup may auto-resume | Startup **always** land here if orphan Real; **never** auto-resume |
| `STOPPING` / `STOPPED` | Unchanged | Unchanged; discard pendings on stop |

`allows_strategy_execution` remains **`RUNNING` only**. While
`RECOVERY_BLOCKED`, no strategy-generated orders. Pending confirmations are
not strategy orders; they are discarded on Real recovery entry.

---

## 6. Validation rules (fail closed)

| Rule | Code (stable suggestion) |
|------|--------------------------|
| `mode` not simulation\|real | `invalid_config` |
| Real allocated > 50 | `real_capital_cap_exceeded` |
| maxPositionSize > allocated | `invalid_config` |
| Confirm after expiry | `pending_confirmation_expired` |
| Confirm with unsafe mark / risk fail | `confirm_validation_failed` |
| Limit order requested | `limit_orders_unavailable` |
| RealExecutionAdapter without credentials | `credentials_missing` |
| Place ack without fill evidence | remain `unsettled` / no position bump |
| Resume Real while reconcile incomplete | `resume_unavailable` |

---

## 7. Relationships

```text
SimulationSessionRow (mode=real)
  ├── 0..1 active PendingEntryConfirmation (pending)
  ├── 0..N RealOrderReconcile rows (history)
  ├── Decision / trade journals (provenance real)
  └── MUST NOT → PortfolioHolding mutations (Sim)
```
