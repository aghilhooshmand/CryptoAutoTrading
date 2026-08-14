# Data Model: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Related**: Constitution XXXIV; Feature 002 public quotes; Feature 003/004
session-run accounting (unchanged)

## Entities

### Portfolio

Singleton local accounting container (`id = 1`).

| Field | Type / notes | Required |
|-------|----------------|----------|
| `quoteCurrency` | `"usdt"` in v1 | yes |
| `bookProvenance` | `local_manual` in 009 | yes |
| `updatedAt` | ISO timestamp of last successful mutation | yes |

Quote cash, reserved, available, equity, P&L, holdings, allocations, positions,
and `warning` / `equityComplete` are **derived** on read (see Snapshot).

**Persistence**: table `portfolio`. After migration, do **not** treat a `cash`
column as authority. Optional leftover `cash` column may be ignored or dropped
once `usdt` holding exists.

### Holding

One balance per asset under the singleton portfolio.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `id` | UUID string | yes |
| `asset` | Canonical lowercase code (`usdt`, `btc`, `eth`, …) unique per portfolio | yes |
| `quantity` | Decimal string, strictly > 0 | yes |
| `averageCost` | Decimal string quote-per-unit; null if unknown | no |
| `realizedPnl` | Decimal string; `"0"` for local/manual in 009 | yes |
| `provenance` | `local_manual` \| `simulation` \| `exchange` | yes |
| `createdAt` / `updatedAt` | ISO timestamps | yes |

**Inspection-only (not stored)**: `price`, `priceStatus` (`fresh` \| `stale` \|
`unavailable`), `marketValue`, `weight`, `unrealizedPnl`, `return`.

The `usdt` holding quantity **is** quote cash. Cost basis of USDT is `1`.

**Persistence**: table `portfolio_holdings`.

### Allocation

Unchanged reservation of **quote cash**.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `id` | UUID string | yes |
| `label` | Operator-facing name | yes |
| `reservedSize` | Decimal string, strictly > 0 (USDT) | yes |
| `targetRef` | Optional non-unique label | no |
| `createdAt` / `updatedAt` | ISO timestamps | yes |

**Persistence**: table `portfolio_allocations`. Release = delete row.

### Position (pipeline view)

Logical only in 009. Always `[]`; deployed always `"0"`. Later features write
through Controller → Risk → Execution — never via strategy or holdings upsert.

### Historical snapshot (persisted, not shown in 009 UI)

| Field | Type / notes | Required |
|-------|----------------|----------|
| `id` | UUID | yes |
| `createdAt` | Time of meaningful book mutation | yes |
| `reason` | `funding` \| `holding_upsert` \| `holding_delete` \| `allocation_create` \| `allocation_resize` \| `allocation_release` | yes |
| `payload` | JSON of the read model at that moment | yes |

**Persistence**: table `portfolio_snapshots`, append-only. No public list API
in Feature 009.

### Read-model snapshot (API/UI)

Projection of Portfolio + Holdings (valued) + Allocations. Not a separate
current-state table.

## Relationships

```text
Portfolio (1)
   ├── Holding (0..N)          # includes usdt = quote cash
   ├── Allocation (0..N)       # reserves quote cash only
   └── Snapshot (0..N)         # history for later analytics
```

Strategies / sessions / XT private accounts are **not** FKs (`targetRef` and
`provenance` are labels/enums).

## Validation rules

1. Money/quantity fields: finite, non-negative decimal strings; holding
   quantity and allocation size strictly > 0.
2. `quote_cash` = USDT holding quantity, or `"0"` if none.
3. `reserved = Σ allocation.reservedSize`.
4. `available = quote_cash − reserved` ≥ 0 ⇒ `reserved ≤ quote_cash`.
5. Funding: resulting `quote_cash ≥ reserved`; else reject.
6. Holdings upsert for `usdt` via generic holdings API → reject (use funding).
7. Non-quote asset must be a supported Feature 002 USDT base (or equivalent
   allowlist); unknown asset → reject.
8. Local/manual provenance for all 009 operator writes.
9. Invalid mutation: no partial write; last good state retained.
10. Strategies cannot create/update/delete portfolio, holding, allocation, or
    snapshot rows.

## Valuation rules (read)

1. USDT: price `"1"`, status `fresh`, value = quantity.
2. Other assets: public quote for `{asset}_usdt`.
3. No usable quote → unvalued: omit value/weight/unrealized; exclude from
   equity.
4. Stale last-known quote → include value; set holding `priceStatus: stale`.
5. `equity` = sum of included market values.
6. `equityComplete` = false if any holding is unvalued.
7. Weights = `marketValue / equity` among valued holdings when equity > 0.
8. Unrealized P&L / return only if `averageCost` and market value both known.

## State transitions

### Quote cash (USDT holding)

```text
[no usdt / quantity 0]
      │ funding set (cash ≥ reserved)
      ▼
[funded]
      │ funding increase / decrease with cash' ≥ reserved → ok
      │ funding decrease with cash' < reserved → reject
```

### Non-quote holding

```text
(none) ──upsert──► active ──upsert──► active'
                      │
                      └──delete──► (removed)
```

Does not change reserved allocations.

### Allocation

```text
(none) ──create──► active ──resize──► active'
                      │
                      └──release──► (removed)
```

No trading/deployed allocation states in Feature 009.

### Snapshot

```text
successful funding | holding upsert/delete | allocation mutation
        │
        ▼
  append snapshot row
```

GET does not append.

## Invariants (after every successful write)

- `quote_cash ≥ 0`
- `reserved ≥ 0`
- `available = quote_cash − reserved ≥ 0`
- `deployed = 0` (Feature 009)
- `positions = []` (Feature 009)
- USDT holding quantity equals quote cash used in allocation checks
- No strategy-owned balances
- Snapshots exist for that mutation (best-effort after commit; do not fail the
  operator mutation if snapshot insert fails — log/warn; prefer including
  snapshot in the same transaction)

Prefer **same transaction** as the book mutation so history cannot diverge.

## Fail-closed load

If stored portfolio/holding/allocation data cannot be interpreted safely: do
not invent quantities, cash, or prices; surface `warning`; refuse unsafe
mutations until repaired. Unvalued holdings must not silently complete equity
(`equityComplete: false`).
