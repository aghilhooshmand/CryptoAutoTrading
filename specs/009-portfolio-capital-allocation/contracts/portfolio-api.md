# Contract: Portfolio & Allocations API

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Consumer**: Portfolio primary UI  
**Depends on**: Shared local SQLite; no strategy registry dependency for core
capital ops (`targetRef` is an opaque optional string)

Local/unauthenticated. No WebSockets. No trading side effects (no session
start/stop, no orders).

JSON field names are camelCase, aligned with existing APIs. Money amounts are
decimal **strings**.

---

## Portfolio snapshot (read model)

```json
{
  "cash": "1000",
  "reserved": "400",
  "available": "600",
  "deployed": "0",
  "realizedPnl": "0",
  "unrealizedPnl": "0",
  "equity": "1000",
  "positions": [],
  "allocations": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
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

| Field | Notes |
|-------|--------|
| `reserved` | Sum of allocation `reservedSize` |
| `available` | `cash − reserved` |
| `equity` | v1 flat: equals `cash` |
| `deployed` | Always `"0"` in Feature 009 |
| `positions` | Always `[]` in Feature 009 |
| `warning` | Non-null when fail-closed recovery applies |

---

## `GET /portfolio`

Return the current portfolio snapshot including allocations.

| Case | Behavior |
|------|----------|
| No row yet / unfunded | Return cash `"0"`, empty allocations, derived zeros (or equivalent empty funded state); `warning` null unless corrupt |
| Corrupt stored state | Fail closed with `warning`; do not invent capital |

**Response**: `200` + snapshot body.

---

## `PUT /portfolio/funding`

Set or adjust portfolio cash (controlled funding).

### Request

```json
{
  "cash": "1000"
}
```

| Rule | Behavior |
|------|----------|
| `cash` missing / non-numeric / negative | `400` invalid |
| `cash < current reserved` | `400` with clear message; prior state unchanged |
| Valid | Persist cash; return updated snapshot |

**Response**: `200` + snapshot.  
**Side effects**: None on Simulation/Backtest/Comparison.

---

## `POST /portfolio/allocations`

Create an allocation reservation.

### Request

```json
{
  "label": "RSI sleeve",
  "reservedSize": "250",
  "targetRef": "rsi"
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `label` | yes | Non-empty trim |
| `reservedSize` | yes | Decimal string > 0 |
| `targetRef` | no | Opaque string; may duplicate other allocations |

| Rule | Behavior |
|------|----------|
| Resulting `reserved > cash` | `400`; prior state unchanged |
| Valid | Create row; return updated snapshot (or created allocation + snapshot) |

**Response**: `201` + snapshot (preferred) or `201` + allocation with client
re-GET. Contract tests SHOULD assert snapshot invariants after create.

---

## `PATCH /portfolio/allocations/{id}`

Resize an existing allocation.

### Request

```json
{
  "reservedSize": "300"
}
```

| Rule | Behavior |
|------|----------|
| Unknown id | `404` |
| `reservedSize` ≤ 0 or invalid | `400` |
| Resulting total reserved > cash | `400`; unchanged |
| Valid | Persist; return snapshot |

Optional later: allow `label` / `targetRef` patch in same endpoint if useful;
not required for MVP if create+release covers rename via recreate.

---

## `DELETE /portfolio/allocations/{id}`

Release (remove) an allocation and free its reserved capital.

| Rule | Behavior |
|------|----------|
| Unknown id | `404` |
| Valid | Delete; return snapshot (`200`) |

UI MUST confirm before calling delete (destructive reservation release).

---

## Error shape

Align with existing APIs:

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

Suggested codes: `invalid_config`, `not_found`, `conflict` (optional).

---

## Invariants (every successful mutating response)

- `available == cash - reserved` (decimal-equal)
- `reserved == sum(allocations.reservedSize)`
- `deployed == "0"`
- `positions` is `[]`
- No calls to create/start simulation, backtest, or comparison

---

## Frontend contract notes

- Portfolio page: fund → allocate → inspect; show units (USDT); help for
  available/reserved/deployed.
- Busy/disable on submit; surface `message` from errors next to the action.
- Confirm before release.
- ~375px usable; inherit `docs/UI_UX_STANDARDS.md`.
- Do not remount unrelated Auto Trading drafts when funding/allocating.
