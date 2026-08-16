# Contract: Real session API

**Feature**: `015-controlled-real-execution`  
**Date**: 2026-08-16  
**Kind**: HTTP JSON (camelCase), local operator API  
**Depends on**: Existing `/simulation/sessions` surface; Feature 013 credentials
for live place/reconcile

See also: [confirmation-gate.md](./confirmation-gate.md),
[data-model.md](../data-model.md).

---

## Mode

`POST /simulation/sessions` (or current create path) accepts:

```json
{
  "mode": "real",
  "symbol": "btc_usdt",
  "allocatedCapital": "25",
  "maxPositionSize": "25",
  "...": "existing session fields"
}
```

| Rule | HTTP | code |
|------|------|------|
| `mode` omitted | treat as `simulation` (unchanged) | — |
| `mode: "real"` + allocated > 50 | 400 | `real_capital_cap_exceeded` |
| `mode: "real"` + invalid maxPosition | 400 | `invalid_config` |
| `mode: "real"` + missing credentials | 503/400 | `credentials_missing` |
| `mode: "real"` + XT free &lt; allocated (when readable) | 400 | `insufficient_xt_free` |
| `mode` other | 400 | `invalid_config` / legacy `real_money_unavailable` removed for valid real |

Real create **MUST NOT** mutate Simulation Portfolio holdings/reservations.

For Real, `startingCapital` / session budget cash in responses are **local
budget only** and MUST NOT be labeled or implied as XT cash (FR-004b). Prefer
optional reconciled `xtFreeQuote` when available.

Status / list / history responses **MUST** include `"mode": "real"` so clients
cannot confuse with simulation.

---

## Confirm / decline pending entry

### `POST /simulation/sessions/{id}/confirm-entry`

Body optional/empty or `{ "pendingConfirmationId": "..." }` when id required.

**Success path:** final validation (incl. XT free ≥ notional) →
RealExecutionAdapter market BUY → reconcile → 200 with updated session status
(full fill may leave RUNNING; partial → exposure + `RECOVERY_BLOCKED`;
timeout/unsettled → retain order id + blocked — never invent fill).

**Failure examples:**

| Situation | code |
|-----------|------|
| No pending | `no_pending_confirmation` |
| Expired | `pending_confirmation_expired` |
| Validation fail | `confirm_validation_failed` |
| XT free insufficient / unreadable | `insufficient_xt_free` / `confirm_validation_failed` |
| Cap would exceed | `real_capital_cap_exceeded` |
| Credentials | `credentials_missing` |
| XT reject | `xt_order_rejected`; no invented fill |
| Timeout / unclear | `xt_reconcile_unsettled`; order retained when known; blocked |

### `POST /simulation/sessions/{id}/decline-entry`

Discards pending; no XT order; session stays `RUNNING` unless otherwise
stopping.

---

## Resume / stop (Real blocked)

Existing resume/stop routes apply. For `mode=real` in `RECOVERY_BLOCKED`:

- Resume unavailable unless Real reconcile + safety gates pass
  (`resume_unavailable`).
- Stop/Flatten must not require entry confirmation.

---

## Non-goals (HTTP)

- No generic `POST /xt-account/orders` place endpoint for arbitrary clients.
- No limit-order placement fields accepted for Real MVP
  (`limit_orders_unavailable`).
