# Data Model: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Related**: Constitution XXXIV; Feature 003/004 session-run accounting (unchanged)

## Entities

### Portfolio

Singleton local capital container (`id = 1`).

| Field | Type / notes | Required |
|-------|----------------|----------|
| `cash` | Decimal string (USDT-oriented) | yes |
| `reserved` | Decimal string — **derived** sum of allocation reserved sizes | derived |
| `available` | Decimal string — **derived** `cash − reserved` | derived |
| `deployed` | Decimal string — **0** in Feature 009 | yes |
| `realizedPnl` | Decimal string — **0** until later binding | yes |
| `unrealizedPnl` | Decimal string — **0** until later binding | yes |
| `equity` | Decimal string — for v1 flat portfolio: equals `cash` (no MTM positions) | derived |
| `positions` | List — **empty** in Feature 009 | yes |
| `updatedAt` | ISO timestamp of last successful mutation | yes |
| `warning` | Optional fail-closed recovery message on read | no |

**Persistence**: one SQLite row table `portfolio` with fixed primary key `1`.
Store `cash`, `deployed`, `realized_pnl`, `unrealized_pnl`, `updated_at`.
Compute `reserved` / `available` / `equity` / `positions` in the service layer
on read.

**Not stored in v1**:
- Exchange balances, credentials, real-money flags
- Mark-to-market position lots (empty until later features)
- Settings FK (Settings remain defaults only)

### Allocation

Explicit reservation of portfolio capital.

| Field | Type / notes | Required |
|-------|----------------|----------|
| `id` | UUID string | yes |
| `label` | Operator-facing name | yes |
| `reservedSize` | Decimal string, strictly > 0 | yes |
| `targetRef` | Optional strategy/program label string (non-unique) | no |
| `createdAt` | ISO timestamp | yes |
| `updatedAt` | ISO timestamp | yes |

**Persistence**: table `portfolio_allocations` with FK to portfolio singleton.
Release = delete row (frees reserved immediately).

**Allocation-level accounting in 009**: reserved size is mandatory; performance
fields may show zeros / “no activity yet” until later binding.

### Position (portfolio view)

Logical entity for FR-001 completeness. In Feature 009 the list is always
empty. Later features may add symbol/side/qty/notional through the trading
pipeline — never via strategy-side mutation.

### Capital Snapshot

API/UI projection of Portfolio + Allocations at read time for inspection and
tests. Not a separate persisted table in v1.

## Relationships

```text
Portfolio (1)
   └── Allocation (0..N)
```

Strategies / sessions / runs are **not** FKs of Allocation in 009
(`targetRef` is a non-authoritative string only).

## Validation rules

1. All money fields: finite, non-negative decimal strings (allocation size > 0).
2. `reserved = Σ allocation.reservedSize`.
3. `available = cash − reserved` ≥ 0 ⇒ `reserved ≤ cash`.
4. Create/resize allocation: resulting reserved must satisfy (3).
5. Funding set/adjust: resulting `cash ≥ reserved`; else reject.
6. Release allocation: removes its reserved size; available increases.
7. Invalid mutation: no partial write; last good state retained.
8. Strategies cannot create/update/delete portfolio or allocation rows.

## State transitions

### Portfolio cash

```text
[unfunded / cash=0]
      │ funding set (cash ≥ 0)
      ▼
[funded]
      │ funding increase
      ▼
[funded']
      │ funding decrease with cash' ≥ reserved → ok
      │ funding decrease with cash' < reserved → reject
```

### Allocation

```text
(none) ──create──► active ──resize──► active'
                      │
                      └──release──► (removed)
```

No “trading” or “deployed” allocation states in Feature 009.

## Invariants (must hold after every successful write)

- `cash ≥ 0`
- `reserved ≥ 0`
- `available = cash − reserved ≥ 0`
- `deployed = 0` (Feature 009)
- `positions = []` (Feature 009)
- No strategy-owned balances

## Fail-closed load

If stored portfolio/allocation data cannot be interpreted safely: do not invent
capital; surface a clear `warning` and a recoverable empty/safe posture defined
in service (e.g. refuse mutations until operator re-funds after reset path if
added). Prefer reject-on-read-corruption over silent repair that creates money.
