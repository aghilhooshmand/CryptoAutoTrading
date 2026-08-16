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

- `mode=real` create: `allocated_capital ≤ 50`; `0 < max_position_size ≤
  allocated_capital`.
- For Real, persist `starting_capital = allocated_capital`. Initial `cash` is
  set to the same value as a **local budget / configuration ceiling only**
  (FR-004b). These fields MUST NOT be presented or treated as actual XT cash.
- Actual available balance and post-trade cash/position MUST come from XT
  reconciliation (Feature 013 / FR-006). Prefer separate API fields for
  reconciled XT free/available when shown to operators.
- Credentials required at create (`credentials_missing` if absent). When XT
  balances are successfully read at create, fail closed if free USDT &lt;
  `allocated_capital` (FR-004a).
- Real create **MUST NOT** call Simulation Portfolio reserve / bind that
  mutates Sim holdings (no `allocation_id` Portfolio write path for Real MVP).
- Simulation create behavior unchanged.

**Operator-visible provenance:** status/history always include `mode` and,
for Real, never imply `simulation` portfolio provenance or that budget cash
equals XT cash.

---

## 2. PendingEntryConfirmation

Represents an approved exposure-increasing BUY awaiting operator action.

| Field | Type | Rules |
|-------|------|-------|
| `id` | UUID string | Primary key |
| `session_id` | UUID string | FK to session; at most **one** non-terminal pending per session |
| `symbol` | string | Must match session symbol |
| `side` | string | `BUY` only for MVP |
| `proposed_notional` / sizing fields | decimal strings | Bounded by session budget caps, maxPositionSize, 50 USDT; confirm also gates on XT free (FR-004a) |
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
| `xt_order_id` | string \| null | Set when XT accepts place; **retain on poll timeout** when known (FR-006c) |
| `side` | `BUY` \| `SELL` | |
| `order_type` | `MARKET` | Only MARKET in MVP |
| `submit_status` | string | `not_submitted` \| `submitted` \| `submit_failed` |
| `reconcile_status` | string | `unsettled` \| `filled` \| `partial_filled_blocked` \| `rejected` \| `unknown_fail_closed` |
| `filled_qty` / `avg_price` / `fee` | decimal strings \| null | **Only** from XT reconcile |
| `updated_at` | datetime | |

**Invariants:**

- Session position/cash for Real update **only** from XT reconcile evidence —
  never from submission ack alone, never from local budget cash as if it were
  XT truth.
- **Full fill**: `reconcile_status=filled`; apply exposure; session may remain
  trading-eligible when otherwise safe.
- **Partial fill (FR-006b)**: record actual `filled_qty` / price as Real
  exposure; set `partial_filled_blocked` (or equivalent); move session to
  `RECOVERY_BLOCKED`; no normal strategy trading until Resume after safe
  reconcile or Stop/Flatten.
- **Poll timeout / unclear (FR-006c)**: keep `xt_order_id` when known; set
  `unsettled` / `unknown_fail_closed`; block new orders; later reconcile must
  determine outcome. Do **not** invent a fill or drop the order identity.

---

## 4. Session status additions (API)

| Field | Meaning |
|-------|---------|
| `mode` | `real` \| `simulation` |
| `pendingConfirmation` | null or summary (id, expiresAt, symbol, sizing) |
| `realReconcile` | optional summary (unsettled / partial-blocked / order id) |
| `budgetStartingCapital` / budget cash | Local budget only — must not be labeled as XT cash |
| `xtFreeQuote` (optional) | Last reconciled free USDT when available |
| `recoveryReason` / blocked flags | Real blocked recovery messaging |

---

## 5. State machine notes

| State | Simulation (014) | Real (015) |
|-------|------------------|------------|
| `RUNNING` | Normal; may auto-recover into it | Normal; may hold pending confirm |
| `RECOVERY_BLOCKED` | Resume after gates; startup may auto-resume | Startup orphans; **also** partial fill / unsettled timeout (FR-006b/c); **never** auto-resume |
| `STOPPING` / `STOPPED` | Unchanged | Unchanged; discard pendings on stop |

`allows_strategy_execution` remains **`RUNNING` only**. While
`RECOVERY_BLOCKED`, no strategy-generated orders and no new Real orders until
reconcile settles. Pending confirmations are discarded on Real recovery entry
(restart path).

---

## 6. Validation rules (fail closed)

| Rule | Code (stable suggestion) |
|------|--------------------------|
| `mode` not simulation\|real | `invalid_config` |
| Real allocated > 50 | `real_capital_cap_exceeded` |
| maxPositionSize > allocated | `invalid_config` |
| Confirm after expiry | `pending_confirmation_expired` |
| Confirm with unsafe mark / risk fail | `confirm_validation_failed` |
| XT free USDT &lt; intended notional / unreadable | `insufficient_xt_free` or `confirm_validation_failed` |
| Limit order requested | `limit_orders_unavailable` |
| RealExecutionAdapter without credentials | `credentials_missing` |
| Place ack without fill evidence | remain `unsettled`; no invented full fill |
| Partial fill recorded | `partial_filled_blocked` + `RECOVERY_BLOCKED` |
| Poll timeout with known/possible order | `xt_reconcile_unsettled`; retain order id; block new orders |
| Resume Real while reconcile incomplete | `resume_unavailable` |

---

## 7. Relationships

```text
SimulationSessionRow (mode=real)
  ├── local budget fields (NOT XT cash)
  ├── 0..1 active PendingEntryConfirmation (pending)
  ├── 0..N RealOrderReconcile rows (history)
  ├── Decision / trade journals (provenance real)
  └── MUST NOT → PortfolioHolding mutations (Sim)
```
