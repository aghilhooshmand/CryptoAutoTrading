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

## Fill semantics

1. Place order → record `xt_order_id` if accepted; `submit_status=submitted`.
2. Poll / read `GET /v4/order/{orderId}` (and balances as needed) until terminal
   filled or rejected/unknown.
3. **Submission MUST NEVER** set session position/cash as filled.
4. On proven fill: return `FillResult(ok=True, fill=..., qty=...)` from XT
   evidence; update Real local ledger only.
5. On reject / timeout / contradictory state: `FillResult(ok=False, ...)` /
   `reconcile_status=unknown_fail_closed`; no invented fill.

Bounded poll timeout is an implementation parameter; unclear outcome fails
closed.

---

## ExecutionIntent

Reuse Feature 012 `ExecutionIntent`. Real adapter ignores Simulation
fee/slippage inventiveness for fill price; may still use intent sizing bounds
(`cash`, `allocated_capital`, `max_position_size`) and `is_forced_close` for
flatten path. Reference price is advisory for validation, not forced fill
price.

---

## Failure codes (stable additions)

| Code | Meaning |
|------|---------|
| `credentials_missing` | No XT private credentials |
| `limit_orders_unavailable` | Non-market requested |
| `xt_order_rejected` | Exchange rejected place |
| `xt_reconcile_unsettled` | Ack/uncertain; no fill applied |
| `real_capital_cap_exceeded` | Would breach 50 USDT / session bounds |
| `real_execution_unavailable` | Reserved for misconfiguration / disabled |

---

## Client boundary

`XtPrivateClient.place_market_order` (name flexible) is internal. Contract
tests MUST continue to ensure Feature 013 **HTTP** surface has no arbitrary
place/cancel/withdraw routes. Session confirm-entry is the operator HTTP
entry to eventually reach the adapter.
