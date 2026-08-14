# Research: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Spec**: [spec.md](./spec.md)

Reservation research (singleton SQLite, `/portfolio`, `available = cash −
reserved`, explicit USDT funding, non-unique `targetRef`) remains in force.
This document replaces the local/manual holdings decisions.

## Decision 1: One book — USDT holding is quote cash

**Decision**: Unchanged. `portfolio_holdings.usdt` quantity **is** quote cash.
Funding upserts that holding. Allocations read USDT quantity, not a parallel
cash ledger.

**Migration**: Leftover `portfolio.cash` still copies once into `usdt` if no
row exists. Rewrite `local_manual` provenance to `simulation`.

## Decision 2: No operator crypto entry (replaces local/manual holdings)

**Decision**: Remove public `PUT`/`DELETE /portfolio/holdings` and the
Portfolio asset-entry form. The operator funds **simulation USDT only**.
BTC/ETH/SOL (and other bases) appear only from simulated fills.

**Rationale**: Locked product direction. Manual quantity forms are a
bookkeeping sandbox, not an exchange portfolio.

**Alternatives considered**:
- Keep hidden upsert for tests — rejected for the public API; tests call the
  domain `apply_simulation_fill` helper instead.
- Seed demo BTC — rejected.

## Decision 3: Fill apply after Simulation Execution

**Decision**: After Feature 003 `_apply_fill` has written the session cash
update and trade journal row, call `portfolio.apply_simulation_fill` in the
**same SQLAlchemy session** with:

- `asset` = session base currency (from `symbol`, e.g. `btc_usdt` → `btc`)
- `side` BUY/SELL
- `qty`, `fill.cash_delta`, `fill.fill_price` (average-cost input)

BUY: USDT += cash_delta (negative; already net of Feature 003 fees/slippage);
increase asset qty; update average cost (weighted). SELL: decrease asset qty
(delete row at 0); USDT += cash_delta; SELL realized P&L delta =
`(fill.fill_price − average_cost) × qty` when average_cost is known —
otherwise leave realized unchanged and do not invent. Do **not** invent a
second fee line inside holding realized P&L; fee drag appears in quote cash /
equity via `cash_delta`. Snapshot reason `simulation_fill`. Successful apply
**clears** persisted `fillApplyWarning`.

If applying the cash_delta would make USDT negative, **or** SELL `qty`
exceeds the current holding quantity for that asset (no shorts in 009):

1. Do not mutate holdings.
2. Do not append a `simulation_fill` snapshot.
3. Persist `fillApplyWarning` on the portfolio row (operator-visible).
4. **Catch** the refusal in `_apply_fill`; do **not** raise out of the
   session transaction. Feature 003 journals and session cash remain as
   already written.

GET `/portfolio` `warning`: corrupt-state message if the book is corrupt;
otherwise `fillApplyWarning` if set; otherwise `null`. GET does not snapshot
and does not clear the warning.

**Rationale**: Constitution VIII (do not invent balances) outranks applying a
fill the Simulation Portfolio cannot fund. Feature 003 cash checks remain
authoritative for the **session**. Unifying session starting cash with
Portfolio available is out of 009/010 scope.

**Alternatives considered**:
- Raise from apply and roll back the session fill — rejected (would rewrite
  Feature 003 journals and break FR-009 compatibility).
- Rewrite session cash to use portfolio as the only wallet now — rejected for
  009 (would churn Feature 003 tests and Auto Trading setup).
- Apply Backtest fills too — rejected (FR-009; Backtest stays on run ledger).
- Invent the missed holding later when the operator funds USDT — rejected
  (would fabricate a fill).

## Decision 3b: Deployed and positions are a session projection

**Decision**: On GET, scan Feature 003 sessions in `RUNNING` or `STOPPING`
with `position_side == long`. Each becomes one `positions[]` entry
(`sessionId`, `symbol`, `asset`, `side`, `quantity`, `costBasis` when
stored). `deployed` is the sum of those `cost_basis` values as USDT, or
`"0"` if none. Do not persist deployed on `portfolio.deployed` as authority
(column may remain leftover cache). Do not constrain allocation
resize/release by deployed in 009.

**Rationale**: Spec clarification still in force; compact Capital UI needs
Deployed. Per-allocation deployed is Feature 010.

## Decision 4: Valuation via Feature 002 public quotes

**Decision**: Unchanged: `{asset}_usdt` via `get_quote`; 60s stale; USDT 1:1
fresh; never invent; unvalued excluded; `equityComplete` false if any
unvalued. USDT unrealized P&L is **null** (not `"0"`).

## Decision 5: Snapshots on meaningful changes

**Decision**: Append on funding, `simulation_fill`, allocation
create/resize/release. Not on GET or price ticks. No snapshot list API. No
history charts. Current-state weight donut is allowed.

## Decision 6: P&L honesty

**Decision**: Unrealized/return only with cost basis **and** usable value.
Realized updates on simulated SELL. Book totals sum known holding figures.
USDT has no artificial unrealized P&L.

## Decision 7: Provenance is simulation in 009

**Decision**: `bookProvenance` and new/updated holdings use `simulation`.
UI: “Simulation Portfolio”, Simulation badge/mode — never “XT account”.
Enum still allows `exchange` for Feature 012. Do not write `local_manual`
going forward.

## Decision 8: Extend existing package; compact allocations

**Decision**: Keep identity, allocations, funding, valuation, snapshots.
Demote allocation UI to a compact/expandable Capital block (Available,
Reserved, Deployed + optional allocation list). Do not delete the allocation
API.

## Decision 9: Package layout

**Decision**: Keep `app.portfolio`. Add fill-apply on the service. Hook from
`session_service._apply_fill` only (after the journal row; catch refuse).
Strategies never import portfolio writes. GET projects `deployed`/`positions`
from Feature 003; do not treat `portfolio.deployed` as authority.
