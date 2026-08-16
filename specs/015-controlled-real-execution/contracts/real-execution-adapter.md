# Contract: RealExecutionAdapter

**Feature**: `015-controlled-real-execution`  
**Date**: 2026-08-16  
**Kind**: Internal Python execution adapter + XT write binding  
**Supersedes**: Feature 012 Real stub (`real_execution_unavailable` for live
Controlled Real path — stub behavior remains only when Real path disabled /
miswired)

---

## Sole write path

Only `RealExecutionAdapter` may place XT trading orders from an approved Real
session intent. Strategies, Controller, Risk, UI, and Feature 013 read routes
MUST NOT place orders.

Simulation / Historical adapters MUST NOT call XT private writes.

---

## Order style (MVP)

| Field | Value |
|-------|-------|
| Exchange | XT Spot `https://sapi.xt.com` |
| Method | `POST /v4/order` (signed; Feature 013 signing) |
| `bizType` | `SPOT` |
| `type` | `MARKET` only |
| `side` | `BUY` \| `SELL` |

Limit / other types → fail closed (`limit_orders_unavailable`).

---

## Pre-submit gates (entries)

Before MARKET BUY place:

1. Session caps (`allocatedCapital` ≤ 50, maxPositionSize, budget bounds).
2. **XT free USDT ≥ intended notional** via Feature 013 (FR-004a); missing /
   failed balance read → fail closed.
3. Local budget fields are **not** proof of XT cash (FR-004b).

---

## Fill semantics

1. Place order → record `xt_order_id` if accepted; `submit_status=submitted`.
2. Poll / read `GET /v4/order/{orderId}` (and balances as needed) within a
   **≤ 5 second** wall-clock place+reconcile budget (FR-006c).
3. **Submission MUST NEVER** alone set session position/cash as filled.
4. **Full fill** within budget: return `FillResult(ok=True, fill=..., qty=...)`
   from XT evidence; update Real local ledger from reconcile only.
5. **Partial fill** (FR-006b): apply actual filled qty/price as Real exposure
   from XT evidence; set `reconcile_status=partial_filled_blocked` (or
   equivalent); caller MUST move session to fail-closed /
   `RECOVERY_BLOCKED` — no normal strategy trading until Resume/Stop.
6. **Timeout / unclear** (FR-006c): MUST NOT forget the order. Persist
   `xt_order_id` when known; set `unsettled` / `unknown_fail_closed`; block new
   orders; return non-success for “clean trading continue”; subsequent
   reconciliation MUST determine actual XT outcome before any new order.
   Timeout MUST NOT invent a fill or clear known exposure blindly.
7. **Reject** with no fill: `submit_failed` / `rejected`; no invented position.

---

## ExecutionIntent

Reuse Feature 012 `ExecutionIntent`. Real adapter ignores Simulation
fee/slippage inventiveness for fill price; may still use intent sizing bounds
(`cash` as **budget hint only**, `allocated_capital`, `max_position_size`) and
`is_forced_close` for flatten path. Reference price is advisory for
validation, not forced fill price. Intent `cash` MUST NOT be treated as XT
free balance (FR-004b).

---

## Failure / status codes (stable additions)

| Code | Meaning |
|------|---------|
| `credentials_missing` | No XT private credentials |
| `limit_orders_unavailable` | Non-market requested |
| `xt_order_rejected` | Exchange rejected place |
| `insufficient_xt_free` | XT free USDT below intended notional / unreadable |
| `xt_reconcile_unsettled` | Timeout/unclear; order retained when known; blocked |
| `partial_filled_blocked` | Partial exposure recorded; session must block |
| `real_capital_cap_exceeded` | Would breach 50 USDT / session bounds |
| `real_execution_unavailable` | Reserved for misconfiguration / disabled |

---

## Client boundary

`XtPrivateClient.place_market_order` (name flexible) is internal. Contract
tests MUST continue to ensure Feature 013 **HTTP** surface has no arbitrary
place/cancel/withdraw routes. Session confirm-entry is the operator HTTP
entry to eventually reach the adapter.
