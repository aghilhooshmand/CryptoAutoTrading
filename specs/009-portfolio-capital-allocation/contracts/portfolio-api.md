# Contract: Simulation Portfolio API

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Consumer**: Portfolio primary UI (Simulation Portfolio)  
**Depends on**: Shared SQLite; Feature 002 public quotes; Feature 003 fills
applied in-process (not via this HTTP API); no XT private APIs

Local/unauthenticated. JSON camelCase. Money and quantities are decimal
**strings**. Null means unknown — never a fabricated number.

Funding and allocation HTTP routes do not start Simulation. Fill-driven
holding changes occur inside the Simulation execution path.

---

## Portfolio snapshot (read model)

```json
{
  "quoteCurrency": "usdt",
  "bookProvenance": "simulation",
  "mode": "simulation",
  "cash": "800",
  "reserved": "250",
  "available": "550",
  "deployed": "0",
  "realizedPnl": "0",
  "unrealizedPnl": "50",
  "totalPnl": "50",
  "totalReturn": "0.05555556",
  "equity": "1250",
  "equityComplete": true,
  "unvaluedAssets": [],
  "positions": [],
  "holdings": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "asset": "usdt",
      "quantity": "800",
      "averageCost": "1",
      "price": "1",
      "priceStatus": "fresh",
      "marketValue": "800",
      "weight": "0.64",
      "realizedPnl": "0",
      "unrealizedPnl": null,
      "return": null,
      "provenance": "simulation",
      "createdAt": "2026-08-14T12:00:00.000Z",
      "updatedAt": "2026-08-14T12:10:00.000Z"
    },
    {
      "id": "22222222-2222-2222-2222-222222222222",
      "asset": "btc",
      "quantity": "0.005",
      "averageCost": "80000",
      "price": "90000",
      "priceStatus": "stale",
      "marketValue": "450",
      "weight": "0.36",
      "realizedPnl": "0",
      "unrealizedPnl": "50",
      "return": "0.125",
      "provenance": "simulation",
      "createdAt": "2026-08-14T12:10:00.000Z",
      "updatedAt": "2026-08-14T12:10:00.000Z"
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
  "updatedAt": "2026-08-14T12:10:00.000Z",
  "warning": null
}
```

`weight` is a ratio string (`"0.50"` = 50%). UI may show `%`. `mode` is
`"simulation"` in Feature 009.

| Field | Notes |
|-------|--------|
| `cash` | USDT holding quantity |
| `available` | `cash − reserved` |
| `equity` | Sum of valued `marketValue` |
| `equityComplete` | `false` if any holding is unvalued |
| `totalPnl` / `totalReturn` | Combined P&L / return when defined; else `null` |
| `bookProvenance` / holding `provenance` | `simulation` in 009 |
| `deployed` | Sum of `costBasis` on `positions`, or `"0"` |
| `positions` | Active Feature 003 longs (`RUNNING`/`STOPPING`); else `[]` |
| `warning` | Corrupt-state message, else persisted fill-apply refusal, else `null` |

USDT `unrealizedPnl` and `return` are `null`. Holding value/price/weight/
unrealized/return are `null` when unknown. Missing price is **not** `"0"`.

---

## `GET /portfolio`

Valued current snapshot. **Does not** append a historical snapshot.

| Case | Behavior |
|------|----------|
| Unfunded | `cash` `"0"`, no non-USDT holdings, `equity` `"0"` |
| After funding only | USDT holding; no BTC/ETH unless fills occurred |
| Unvalued holding | Quantity shown; `equityComplete` false |
| Active sim long | `positions` non-empty; `deployed` = sum of those cost bases |
| Refused fill-apply | Holdings unchanged vs last success; `warning` is the fill-apply text (unless corrupt-state supersedes) |
| Corrupt stored state | Fail closed with `warning` (corrupt message wins) |

**Response**: `200` + snapshot.

---

## `PUT /portfolio/funding`

Set simulation quote cash (USDT holding).

```json
{ "cash": "1000" }
```

| Rule | Behavior |
|------|----------|
| missing / non-numeric / negative | `400` |
| `cash < reserved` | `400`; prior state unchanged |
| Valid | Upsert `usdt`; provenance `simulation`; snapshot `funding`; return snapshot |

Does not start Simulation. Does not create BTC/ETH rows.

---

## Holdings writes (removed from public API)

There is **no** public operator `PUT /portfolio/holdings` or
`DELETE /portfolio/holdings/{asset}`.

| Method | Path | Behavior |
|--------|------|----------|
| `PUT` | `/portfolio/holdings` | `404` or `405` — not an operator holdings book |
| `DELETE` | `/portfolio/holdings/{asset}` | `404` or `405` |

Fill-driven updates are in-process via `apply_simulation_fill` (not HTTP).

---

## `POST /portfolio/allocations`

```json
{ "label": "RSI sleeve", "reservedSize": "250", "targetRef": "rsi" }
```

Reserved vs **quote cash**. Over-reserve → `400`, prior state unchanged.
Success: `201` + snapshot; snapshot reason `allocation_create`.

---

## `PATCH /portfolio/allocations/{id}`

Resize. Unknown id `404`. Reserved > cash → `400`. Success: snapshot
`allocation_resize`.

---

## `DELETE /portfolio/allocations/{id}`

Release. UI SHOULD confirm. Success: snapshot `allocation_release`.

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

## Invariants (successful mutating HTTP responses)

- `available == cash - reserved`
- `reserved == sum(allocations.reservedSize)`
- `cash` equals USDT quantity when that holding exists, else `"0"`
- `equity` equals sum of non-null holding `marketValue`
- `bookProvenance == "simulation"`
- `deployed` / `positions` follow the Feature 003 projection rules
- No simulation **start** as a side effect of funding/allocation HTTP
- A historical snapshot row for that HTTP mutation (same transaction)

Successful fill apply (in-process) must append `simulation_fill` and keep the
same cash/equity invariants. Refused fill apply must not append a snapshot,
must persist `fillApplyWarning`, and must not roll back Feature 003 journals.

Position object (when present):

```json
{
  "sessionId": "44444444-4444-4444-4444-444444444444",
  "symbol": "btc_usdt",
  "asset": "btc",
  "side": "long",
  "quantity": "0.005",
  "costBasis": "200"
}
```

---

## Frontend contract notes

- Title/mode: Simulation Portfolio (badge or equivalent). Not a live XT account.
- Summary cards: total value, available USDT, total P&L/return, realized /
  unrealized P&L.
- Current-state allocation visual (donut or equivalent). No history charts.
- Holdings: asset, quantity, price, value, P&L, weight. Cards at ~375px.
- No form to type BTC/ETH/SOL quantity.
- Compact Capital: available, reserved, deployed; allocations expandable.
- Show GET `warning` when present (not hover-only).
- Confirm allocation release; busy/error/success; `docs/UI_UX_STANDARDS.md`.
