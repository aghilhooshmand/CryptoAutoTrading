# Contract: Simulation Risk API extensions

**Feature**: `010-advanced-risk-management`  
**Date**: 2026-08-14  
**Extends**: Feature 003 `/simulation` create/session read; Feature 008
`/settings`; Feature 009 `/portfolio/allocations`  
**Catalog**: [risk-catalog.md](./risk-catalog.md)

Local/unauthenticated. JSON camelCase. Money/rates as decimal **strings**.

## `POST /simulation/sessions` (create) — added fields

```json
{
  "allocationId": "33333333-3333-3333-3333-333333333333",
  "portfolioMaxLossRate": "0.10",
  "portfolioMaxLossAmount": null,
  "perSymbolMaxWeight": "0.40"
}
```

| Field | Rules |
|-------|--------|
| `allocationId` | Optional. Must exist in Portfolio allocations when set. |
| `portfolioMaxLossRate` / `portfolioMaxLossAmount` | Optional. At least one if portfolio max-loss desired. Amount derived from baseline at **start** when only rate given. |
| `perSymbolMaxWeight` | Optional ratio `> 0` and `≤ 1`. |

### Create/start validation

| Case | Behavior |
|------|----------|
| `allocatedCapital > portfolio.available` | `400` + `insufficient_portfolio_available` |
| Unknown `allocationId` | `400` / `not_found` style error |
| Capital nesting invalid | Existing Feature 003 errors |

On successful **start**, if portfolio max-loss configured, persist frozen
`portfolioLossBaselineKind` + `portfolioLossBaselineValue` on the session.

## Session read model — added fields

```json
{
  "allocationId": "33333333-3333-3333-3333-333333333333",
  "portfolioMaxLossRate": "0.10",
  "portfolioMaxLossAmount": "100",
  "portfolioLossBaselineKind": "equity",
  "portfolioLossBaselineValue": "1000",
  "perSymbolMaxWeight": "0.40"
}
```

Null when unset. Baseline fields null until start freezes them (or null if
max-loss not configured).

## Decision journals

Rejects/stops MUST use catalog `reasonCode` / `reasonMessage`. Multi-rule
failures → **first** failing code only ([risk-catalog.md](./risk-catalog.md)).

## Portfolio allocation mutations (Feature 009 paths)

| Method | Path | New rule |
|--------|------|----------|
| `DELETE` | `/portfolio/allocations/{id}` | If any Simulation is bound to `{id}` → `400` `allocation_release_blocked` |
| `PATCH` | `/portfolio/allocations/{id}` | If bound and `reservedSize < deployed` for that binding → `400` `allocation_resize_blocked` |

## Settings (`GET`/`PUT /settings`) — optional defaults

Added optional fields (same names as create): `portfolioMaxLossRate`,
`portfolioMaxLossAmount`, `perSymbolMaxWeight`, `preferredAllocationId`.

Copy into new Simulation forms only. Never rewrite existing sessions.

## Backtest / Comparison

No new required portfolio fields. Shared Risk runs with portfolio context off.
Existing optional session risk fields unchanged.

## Invariants

- Dual ledger: session cash ≠ Portfolio USDT; Risk reads Portfolio for gates.
- Unbound BUY does not re-check `available`.
- Bound BUY checks allocation remaining only (plus session gates).
- `deployed` not subtracted from `available`.
- No XT private / real-money fields.
