# Data Model: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Related**: Constitution XXXIV; Feature 002 public quotes; Feature 003
fills applied into this domain; Feature 004 journals unchanged

## Entities

### Simulation Portfolio

Singleton (`id = 1`). Operator-visible 009 container.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `quoteCurrency` | `"usdt"` in v1 | yes |
| `bookProvenance` | `simulation` in 009 | yes |
| `fillApplyWarning` | Nullable string; set when fill-apply is refused; cleared on successful apply | no |
| `updatedAt` | Last successful **book** mutation (funding, successful fill apply, allocation_*). Recording a warning without a book change does not require a snapshot. | yes |

Derived on read: cash, reserved, available, equity, P&L, holdings,
allocations, positions, `deployed`, `warning`, `equityComplete`.

`warning` on the read model: corrupt-state message if load is corrupt;
else `fillApplyWarning`; else `null`.

**Persistence**: table `portfolio`. `cash` and `deployed` columns are leftover
cache only — quote cash authority is the `usdt` holding; deployed authority
is the Feature 003 projection.

### Holding

One balance per asset.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `id` | UUID | yes |
| `asset` | Lowercase (`usdt`, `btc`, …) unique per portfolio | yes |
| `quantity` | Decimal string, strictly > 0 | yes |
| `averageCost` | Quote per unit; null if unknown | no |
| `realizedPnl` | Decimal string; updated on simulated SELL | yes |
| `provenance` | `simulation` in 009 (`exchange` reserved for 012) | yes |
| `createdAt` / `updatedAt` | ISO | yes |

Inspection-only: `price`, `priceStatus`, `marketValue`, `weight`,
`unrealizedPnl`, `return`.

USDT quantity **is** quote cash. USDT unrealized P&L is not stored or
invented (inspection: null).

Non-USDT rows are created only by `apply_simulation_fill`, never by operator
upsert.

**Persistence**: `portfolio_holdings`.

### Allocation

Quote-cash reservation. Unchanged semantically.

| Field | Notes |
|-------|--------|
| `id`, `label`, `reservedSize` (> 0), optional `targetRef`, timestamps | |

**Persistence**: `portfolio_allocations`. Release = delete.

### Position (pipeline view)

Derived on GET from Feature 003 sessions in `RUNNING` or `STOPPING` with
`position_side == long`. Otherwise `[]`.

| Field | Notes |
|-------|--------|
| `sessionId` | Feature 003 session id |
| `symbol` | e.g. `btc_usdt` |
| `asset` | Base, e.g. `btc` |
| `side` | `long` |
| `quantity` | Session `position_qty` |
| `costBasis` | Session USDT `cost_basis` when stored; else null |

`deployed` = sum of non-null `costBasis` values, else `"0"`. Distinct from
holdings. Not stored as portfolio authority. Allocation CRUD is **not**
constrained by deployed in 009.

### Historical snapshot

| Field | Notes |
|-------|--------|
| `id`, `createdAt` | |
| `reason` | `funding` \| `simulation_fill` \| `allocation_create` \| `allocation_resize` \| `allocation_release` |
| `payload` | JSON read model |

Append-only. No public list API. GET does not append.

### Read-model snapshot

Valued GET body for the UI.

## Relationships

```text
Simulation Portfolio (1)
   ├── Holding (0..N)       # usdt = quote cash; others from sim fills
   ├── Allocation (0..N)
   └── Snapshot (0..N)
```

## Validation rules

1. Money/quantity: finite, non-negative decimal strings; holding qty and
   allocation size strictly > 0 (zero qty → delete holding).
2. `quote_cash` = USDT quantity or `"0"`.
3. `reserved = Σ reservedSize`; `available = quote_cash − reserved` ≥ 0.
4. Funding: resulting USDT ≥ reserved.
5. No public operator holdings upsert/delete.
6. Fill apply MUST NOT invent negative USDT. Refused apply MUST persist
   `fillApplyWarning` and MUST NOT append `simulation_fill`. The Feature 003
   session transaction MUST still commit.
7. Strategies cannot write portfolio rows.
8. Invalid **portfolio** mutation: no partial persist of that mutation.
   Session journals already written for a fill are not undone.

## Valuation rules (read)

1. USDT: price `"1"`, fresh, value = quantity; unrealized/return null.
2. Other assets: public `{asset}_usdt`.
3. No usable quote → quantity visible; value unknown (**not** zero);
   exclude from equity.
4. Stale last-known → include; `priceStatus: stale`.
5. `equity` = sum of included values; `equityComplete` false if any unvalued.
6. Weights = `marketValue / equity` among valued holdings.
7. Unrealized/return only if average cost and market value both known.

## State transitions

### Quote cash

```text
[unfunded] ──fund (USDT ≥ reserved)──► [funded]
                 │
                 └── decrease below reserved → reject
```

### Non-quote holding

```text
(none) ──simulated BUY──► active ──BUY──► active' (qty/cost up)
                            │
                            └──simulated SELL──► reduced or (removed if qty 0)
```

### Allocation

```text
(none) ──create──► active ──resize──► active'
                      └──release──► (removed)
```

### Snapshot

```text
funding | simulation_fill (success only) | allocation_*  →  append row
GET / price tick / refused fill-apply  →  no row
```

## Invariants

- `available = quote_cash − reserved ≥ 0`
- USDT quantity is the cash used in reservation checks
- No strategy-owned balances
- Snapshots in the same transaction as a **successful** book mutation
- `deployed` / `positions` match active Feature 003 longs on that GET

## Fail-closed load

Corrupt stored money/qty → warning (takes precedence over fill-apply
warning); do not invent. Unvalued holdings must not silently complete equity.
