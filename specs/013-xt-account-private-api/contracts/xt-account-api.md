# Contract: Real XT Account API (read-only)

**Feature**: `013-xt-account-private-api`  
**Date**: 2026-08-16  
**Consumer**: Minimal Real XT inspect UI (`/portfolio/real-xt`)  
**Depends on**: Env credentials `XT_API_KEY` / `XT_API_SECRET`; XT Spot private REST; Feature 002 public market remains independent  
**Non-goals**: Place/cancel; Real trading mode; Portfolio writes; RealExecutionAdapter live fills

Local/unauthenticated app API (same as other operator routes). JSON **camelCase**. Money and quantities are decimal **strings**. Null means unknown — never invent balances or orders on failure.

Provenance is always **`real_xt`**, never `simulation`.

---

## Error envelope

All failures:

```json
{
  "error": {
    "code": "credentials_missing",
    "message": "XT private credentials are not configured."
  }
}
```

### Stable codes → typical HTTP

| code | HTTP (typical) | Meaning |
|------|----------------|---------|
| `credentials_missing` | 503 | Env key/secret missing or blank (fail closed; config unavailable) |
| `authentication_failed` | 401 | XT rejected key/signature/permissions (non-timestamp) |
| `timestamp_invalid` | 401 | XT AUTH_105 / recv-window / clock skew |
| `rate_limited` | 429 | After at most one bounded retry |
| `xt_private_unavailable` | 502 | Timeout, 5xx, malformed envelope (use 503 only if distinguishing transient local unavailability is required later) |
| `order_not_found` | 404 | Order id unknown |

Secrets MUST NOT appear in `message` or logs at info level.

---

## GET `/xt-account/balances`

Returns filtered Real XT balances.

### Success 200

```json
{
  "bookProvenance": "real_xt",
  "retrievedAt": "2026-08-16T01:00:00.000Z",
  "balances": [
    {
      "asset": "usdt",
      "free": "100.5",
      "locked": "10",
      "total": "110.5",
      "provenance": "real_xt"
    }
  ]
}
```

Rules:
- Omit assets with free and locked both zero.
- Empty `balances` array is success.
- Does not read or write `/portfolio`.

---

## GET `/xt-account/open-orders`

Optional query: `symbol` (pass-through to XT when provided).

### Success 200

```json
{
  "bookProvenance": "real_xt",
  "retrievedAt": "2026-08-16T01:00:00.000Z",
  "orders": [
    {
      "orderId": "6216559590087220004",
      "symbol": "BTC_USDT",
      "side": "BUY",
      "orderType": "LIMIT",
      "quantity": "2",
      "price": "40000",
      "executedQty": "1.2",
      "status": "NEW",
      "updatedAt": "2026-08-16T00:55:00.000Z",
      "provenance": "real_xt"
    }
  ]
}
```

Empty `orders` is success.

---

## GET `/xt-account/orders/{orderId}`

### Success 200

```json
{
  "bookProvenance": "real_xt",
  "retrievedAt": "2026-08-16T01:00:00.000Z",
  "order": {
    "orderId": "6216559590087220004",
    "symbol": "BTC_USDT",
    "side": "BUY",
    "orderType": "LIMIT",
    "quantity": "2",
    "price": "40000",
    "executedQty": "1.2",
    "status": "FILLED",
    "updatedAt": "2026-08-16T00:58:00.000Z",
    "provenance": "real_xt"
  }
}
```

### Not found

`404` + `order_not_found`.

---

## Forbidden routes (013)

MUST NOT exist in this feature:

- `POST/DELETE` order placement or cancel under `/xt-account/*`
- Any “Real trading mode” enable endpoint
- Credential upload endpoints

---

## UI contract (operator)

| Surface | Behavior |
|---------|----------|
| Route | `/portfolio/real-xt` |
| Labeling | “Real XT Account” + real-XT badge; not titled Simulation Portfolio |
| Actions | Refresh balances / open orders; order-id lookup — **no** Buy/Sell/Cancel/Place |
| Credentials | Never shown or editable in UI |
| Errors | Show `error.code` + message via existing alert patterns |
| Isolation | Link from Portfolio page OK; do not reuse Portfolio snapshot components as the data source |

---

## Private client obligations (internal)

| Method | Maps to XT |
|--------|------------|
| `get_balances()` | `GET /v4/balances` |
| `list_open_orders(symbol?)` | `GET /v4/open-order` |
| `get_order(order_id)` | `GET /v4/order/{orderId}` |

No `place_order` / `cancel_order` methods in 013.

Rate limit: max one retry; `Retry-After` capped at 3s; else 0.5s backoff; then `rate_limited`.

Signing: HMAC-SHA256 headers per XT v4; recvWindow default 5000 ms.

---

## Amendment 2026-08-17 — Living private-account contract

New Kraken read routes MUST be venue-neutral (example: `/account/*` or
documented equivalent) returning `venue: "kraken"`. Legacy `/xt-account/*`
MAY remain. No place/cancel routes. Secrets never in request bodies or UI.

Kraken adapter methods (internal): `get_balances`, `list_open_orders`,
`get_order` only. No `AddOrder` in 013.
