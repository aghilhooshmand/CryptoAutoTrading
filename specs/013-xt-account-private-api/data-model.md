# Data Model: Feature 013 — XT Account / Private API

**Date**: 2026-08-16  
**Storage**: None — Real XT account data is read-through from XT; not persisted in Feature 009 Portfolio SQLite. No new tables in 013.

---

## Entities

### PrivateCredentials (config, not persisted)

| Field | Type | Rules |
|-------|------|--------|
| api_key | string | From `XT_API_KEY`; non-empty required for private ops |
| api_secret | string | From `XT_API_SECRET`; non-empty required; never logged or returned in API/UI |

**Validation**: Missing either → fail closed `credentials_missing` before network.

---

### RealXtBalance

| Field | Type | Rules |
|-------|------|--------|
| asset | string | Normalized currency id (e.g. `usdt`); required |
| free | decimal string | Available / free amount; required when present from exchange |
| locked | decimal string | Frozen / locked amount; required when present |
| total | decimal string \| null | Exchange `totalAmount` or free+locked when both known; null if not derivable |
| provenance | `"real_xt"` | Always |

**Filter**: Omit when free and locked both normalize to zero. Empty list is valid success.

---

### RealXtOpenOrder

| Field | Type | Rules |
|-------|------|--------|
| orderId | string | Exchange order id |
| symbol | string | Trading pair as returned (e.g. `BTC_USDT`) |
| side | string | e.g. `BUY` / `SELL` |
| orderType | string \| null | e.g. `LIMIT` / `MARKET` when present |
| quantity | decimal string \| null | Original qty when present |
| price | decimal string \| null | Limit price when present |
| executedQty | decimal string \| null | When present |
| status | string | Exchange `state` (e.g. `NEW`, `PARTIALLY_FILLED`) |
| updatedAt | ISO-8601 string \| null | From exchange ms timestamps when present |
| provenance | `"real_xt"` | Always |

Empty open-order list is valid success.

---

### RealXtOrderStatus

Same core fields as open order for a single lookup, plus:

| Field | Type | Rules |
|-------|------|--------|
| orderId | string | Requested id |
| found | bool | false → caller maps to `order_not_found` |

---

### PrivateErrorOutcome

| Field | Type | Rules |
|-------|------|--------|
| code | enum string | One of: `credentials_missing`, `authentication_failed`, `timestamp_invalid`, `rate_limited`, `xt_private_unavailable`, `order_not_found` |
| message | string | Operator-readable; may mention clock skew for `timestamp_invalid`; must not include secrets |

---

### RealXtAccountSnapshot (API aggregate)

| Field | Type | Rules |
|-------|------|--------|
| bookProvenance | `"real_xt"` | Distinguishes from Simulation Portfolio |
| balances | RealXtBalance[] | After zero/zero filter |
| retrievedAt | ISO-8601 | Server time of successful read |

Open orders may be a separate resource rather than nested in the snapshot (see contracts).

---

## Relationships

```text
PrivateCredentials ──authorizes──► XtPrivateClient reads
                                      │
                                      ├──► RealXtBalance[]
                                      ├──► RealXtOpenOrder[]
                                      └──► RealXtOrderStatus

Simulation Portfolio (009) ──no relationship──  Real XT entities
RealExecutionAdapter (012) ──no live use──  XtPrivateClient in 013
```

---

## State transitions

N/A for trading. Account reads are request/response only. Order `status` reflects exchange state; this feature does not transition orders.

---

## Isolation invariants

1. No write path from Real XT entities into Portfolio repository.
2. No merge of `real_xt` and `simulation` provenance in one authoritative book.
3. No place/cancel entities or commands in 013.
