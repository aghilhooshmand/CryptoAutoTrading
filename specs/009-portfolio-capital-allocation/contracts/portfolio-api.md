# Contract: Portfolio, Holdings & Allocations API

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Consumer**: Portfolio primary UI  
**Depends on**: Shared local SQLite; Feature 002 public quotes for valuation;
no strategy registry for core ops (`targetRef` opaque); no XT private APIs

Local/unauthenticated. No WebSockets. No trading side effects (no session
start/stop, no orders).

JSON field names are camelCase. Money and quantities are decimal **strings**.
Null means unknown (cost basis, value, P&L)—never a fabricated number.

---

## Portfolio snapshot (read model)

```json
{
  "quoteCurrency": "usdt",
  "bookProvenance": "local_manual",
  "cash": "500",
  "reserved": "250",
  "available": "250",
  "deployed": "0",
  "realizedPnl": "0",
  "unrealizedPnl": "50",
  "totalPnl": "50",
  "totalReturn": "0.05555556",
  "equity": "950",
  "equityComplete": true,
  "unvaluedAssets": [],
  "positions": [],
  "holdings": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "asset": "usdt",
      "quantity": "500",
      "averageCost": "1",
      "price": "1",
      "priceStatus": "fresh",
      "marketValue": "500",
      "weight": "0.5263",
      "realizedPnl": "0",
      "unrealizedPnl": "0",
      "return": "0",
      "provenance": "local_manual",
      "createdAt": "2026-08-14T12:00:00.000Z",
      "updatedAt": "2026-08-14T12:00:00.000Z"
    },
    {
      "id": "22222222-2222-2222-2222-222222222222",
      "asset": "btc",
      "quantity": "0.005",
      "averageCost": "80000",
      "price": "90000",
      "priceStatus": "stale",
      "marketValue": "450",
      "weight": "0.4737",
      "realizedPnl": "0",
      "unrealizedPnl": "50",
      "return": "0.125",
      "provenance": "local_manual",
      "createdAt": "2026-08-14T12:00:00.000Z",
      "updatedAt": "2026-08-14T12:05:00.000Z"
    }
  ],
  "allocations": [
    {
      "id": "33333333-3333-3333-3333-333333333333",
      "label": "RSI sleeve",
      "reservedSize": "250",
      "targetRef": "rsi",
      "createdAt": "2026-08-14T12:00:00.000Z",
      "updatedAt": "2026-08-14T12:00:00.000Z"
    }
  ],
  "updatedAt": "2026-08-14T12:05:00.000Z",
  "warning": null
}
```

`weight` is a decimal **ratio** string (e.g. `"0.50"` = 50% of known-value
equity), not a percent like Feature 002 `changePercent`. UI may display `%`.

| Field | Notes |
|-------|--------|
| `cash` | Quote-cash = USDT holding quantity (`"0"` if none) |
| `reserved` | Sum of allocation `reservedSize` |
| `available` | `cash − reserved` |
| `equity` | Sum of **valued** holding `marketValue` (known-value equity) |
| `equityComplete` | `false` if any holding is unvalued |
| `unvaluedAssets` | Asset codes excluded from equity |
| `totalPnl` | Realized + unrealized when every holding has defined unrealized P&L; otherwise `null` |
| `totalReturn` | `totalPnl / cost basis` when cost basis exists for every holding; otherwise `null` |
| `deployed` | Always `"0"` in Feature 009 |
| `positions` | Always `[]` in Feature 009 |
| `bookProvenance` | `local_manual` in 009; never imply live XT account |
| `warning` | Fail-closed recovery; not a substitute for `equityComplete` |

Holding inspection nulls when unknown: `price`, `marketValue`, `weight`,
`unrealizedPnl`, `return`, `averageCost`. `priceStatus` is `unavailable` when
there is no usable price. Book `totalPnl` / `totalReturn` are `null` when any
holding lacks a defined unrealized P&L or cost basis.

---

## `GET /portfolio`

Return the current valued snapshot (quotes fetched for this read; **does not**
append a historical snapshot row).

| Case | Behavior |
|------|----------|
| Unfunded | `cash` `"0"`, empty or no USDT holding, empty allocations, `equity` `"0"`, `equityComplete` true unless unvalued leftovers |
| Corrupt stored state | Fail closed with `warning`; do not invent quantities |
| Unvalued holding | Include holding quantity; `equityComplete` false |

**Response**: `200` + snapshot body.

---

## `PUT /portfolio/funding`

Set or adjust **quote cash** (USDT holding).

### Request

```json
{ "cash": "1000" }
```

| Rule | Behavior |
|------|----------|
| missing / non-numeric / negative | `400` |
| `cash < current reserved` | `400`; prior state unchanged |
| Valid | Upsert `usdt` holding; append historical snapshot; return valued snapshot |

**Side effects**: None on Simulation/Backtest/Comparison.

---

## `PUT /portfolio/holdings`

Create or replace a **non-quote** local/manual holding.

### Request

```json
{
  "asset": "btc",
  "quantity": "0.005",
  "averageCost": "80000"
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `asset` | yes | Lowercase; not `usdt`; must be a supported USDT-quoted base |
| `quantity` | yes | Decimal string > 0 |
| `averageCost` | no | Quote per unit; omit/null = unknown |

| Rule | Behavior |
|------|----------|
| `asset` is `usdt` | `400` — use funding |
| unsupported / unknown asset | `400` |
| quantity ≤ 0 or invalid | `400` |
| Valid | Upsert; provenance `local_manual`; does not change reservations; append historical snapshot; return valued snapshot |

**Response**: `200` + snapshot.

---

## `DELETE /portfolio/holdings/{asset}`

Remove a non-quote holding.

| Rule | Behavior |
|------|----------|
| `asset` is `usdt` | `400` — use funding (including setting cash to `0` if reserved allows) |
| Unknown asset | `404` |
| Valid | Delete; append snapshot; return valued snapshot (`200`) |

UI MUST confirm before delete.

---

## `POST /portfolio/allocations`

Unchanged semantically; `reserved` compared to **quote cash** (USDT quantity).

### Request

```json
{
  "label": "RSI sleeve",
  "reservedSize": "250",
  "targetRef": "rsi"
}
```

| Rule | Behavior |
|------|----------|
| Resulting `reserved > cash` | `400`; prior state unchanged |
| Valid | Create; append snapshot; `201` + snapshot |

---

## `PATCH /portfolio/allocations/{id}`

Resize. Unknown id `404`. Resulting reserved > cash → `400`. Success: snapshot
row + `200` snapshot.

---

## `DELETE /portfolio/allocations/{id}`

Release. UI MUST confirm. Success: snapshot row + `200` snapshot.

---

## Error shape

```json
{
  "detail": {
    "error": {
      "code": "invalid_config",
      "message": "Reserved capital cannot exceed cash."
    }
  }
}
```

Codes: `invalid_config`, `not_found`.

---

## Invariants (every successful mutating response)

- `available == cash - reserved` (decimal-equal)
- `reserved == sum(allocations.reservedSize)`
- `cash` equals USDT holding `quantity` when that holding exists, else `"0"`
- `equity` equals sum of non-null holding `marketValue`
- `equityComplete` is false iff `unvaluedAssets` is non-empty
- `deployed == "0"`; `positions` is `[]`
- No simulation/backtest/comparison start
- A historical snapshot row was persisted for this mutation (same transaction)

---

## Frontend contract notes

- Holdings table: asset, quantity, price (stale/unavailable), value, weight %,
  cost basis if known, P&L if known, provenance (local/manual ≠ exchange).
- If `equityComplete` is false, label equity as partial / known-value.
- Show total P&L and total return when defined; otherwise unknown (not invented).
- Fund USDT; separate control to record/adjust/remove non-quote holdings.
- Allocate against available quote cash; confirm release; confirm holding
  delete.
- Busy/disable; errors next to the action; ~375px; `docs/UI_UX_STANDARDS.md`.
- No value-over-time / drawdown charts in Feature 009.
- Do not remount Auto Trading drafts when mutating portfolio.
