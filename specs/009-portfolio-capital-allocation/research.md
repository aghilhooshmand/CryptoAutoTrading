# Research: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Spec**: [spec.md](./spec.md)

Cash-only 009 research (singleton SQLite, `/portfolio`, `available = cash −
reserved`, explicit funding, non-unique `targetRef`, no sim ledger migration)
remains in force for **quote-cash reservation**. This document records holdings
reconcile decisions.

## Decision 1: One book — USDT holding is quote cash

**Decision**: Persist asset balances in `portfolio_holdings`. The `usdt` row
quantity **is** quote cash. Funding `PUT /portfolio/funding` upserts that
holding. Allocation invariants read quote cash from the USDT holding, not from
a parallel cash ledger.

**Migration**: On first load after upgrade, if `portfolio.cash` is set and no
`usdt` holding exists, copy `cash` → `usdt` quantity (provenance
`local_manual`). Thereafter holdings are source of truth. Do not keep two
authoritative cash fields.

**Rationale**: Spec forbids a separate capital portfolio vs asset portfolio.
Existing allocation tests keep the same identity: `available = quote_cash −
reserved`.

**Alternatives considered**:
- Keep `portfolio.cash` as authority and holdings as display-only — rejected
  (two books).
- Equity-as-cash (current code) — superseded by spec.

## Decision 2: Local/manual non-quote holdings

**Decision**: Operator may upsert/delete holdings for **supported** non-quote
assets (quantity > 0; optional average cost). Provenance `local_manual`.
Supported assets = base currencies of Feature 002 USDT-quoted pairs (e.g.
`btc`, `eth`) plus quote `usdt` via funding only. Recording a holding does not
trade, start Simulation, or change allocations.

USDT quantity MUST NOT be writable through the generic holdings upsert (would
bypass reserved-cash checks). Use funding.

**Rationale**: Clarify Q1 (holdings session). Enables multi-asset Portfolio UI
before execution binding without looking like XT private balances.

**Alternatives considered**:
- Funding-only until execution — rejected by clarify.
- Demo seed BTC/ETH — rejected (not operator inventory).

## Decision 3: Capital identity unchanged (quote cash)

**Decision**: `reserved = Σ allocation.reservedSize`; `available = quote_cash −
reserved`; `reserved ≤ quote_cash`. Deployed stays `"0"`; positions `[]` in
009. Allocations reserve USDT, not BTC units. Cross-allocation spend is
rejected by the same reserved-vs-available checks (execution later must use
this identity).

**Rationale**: Clarify Q3 (capital session) still in force.

**Alternatives considered**: Reserve against equity — rejected (would lock BTC
value as spendable cash).

## Decision 4: Valuation via Feature 002 public quotes

**Decision**: On read (and on mutation responses that return the read model),
value each non-USDT holding as `{asset}_usdt` via existing
`MarketDataService.get_quote`. Reuse Feature 002 freshness: prefer
`observedAt` else `retrievedAt`; **> 60s → stale**. USDT values 1:1, always
treated as fresh.

- No usable price → quantity visible; value/weight/unrealized omitted; exclude
  from equity.
- Stale last-known price → include value in equity; per-holding and book-level
  stale indicators.
- Any excluded holding → `equityComplete: false` (partial / known-value
  equity). Weights are shares of known-value equity.

Never invent prices. Tests stub the market service.

Portfolio GET/mutations that need quotes become **async** FastAPI handlers so
they can await `get_quote` without a second HTTP hop.

**Rationale**: Clarify Q3 (holdings session); constitution VIII; Feature 002
already owns XT public access.

**Alternatives considered**:
- Frontend calls `/market/quote` per row — rejected (split authority; easier to
  desync equity).
- Exclude stale from equity — rejected by clarify.

## Decision 5: Snapshots on meaningful book changes only

**Decision**: Append a `portfolio_snapshots` row after successful funding,
holdings upsert/delete, and allocation create/resize/release. Payload = the
read model at that moment (quantities, reservations, valuation if quotes were
fetched for the response). Do **not** snapshot on GET or on price refresh
alone. No `GET /portfolio/snapshots` in Feature 009 (avoids a history UI).
Unit tests assert a row is written on mutation and not on GET.

**Rationale**: Clarify Q2. Prepares later analytics without 009 charts.

**Alternatives considered**:
- Current-state only, no table — rejected by clarify.
- Periodic price snapshots — rejected by clarify.
- Public snapshot list in 009 — rejected (UI would be tempted to chart).

## Decision 6: P&L honesty

**Decision**: Holding unrealized P&L and return only when **both** average cost
and a usable (fresh or stale) market value exist. Holding realized P&L stays
`0` for local/manual bootstrap (no fill). Book realized/unrealized = sums of
known holding figures; unknown cost does not invent unrealized. Do not show
drawdown or equity curves.

**Rationale**: Spec FR-001b / SC-008; constitution VI/XII.

## Decision 7: Provenance for Feature 012 reuse

**Decision**: Holding `provenance` enum: `local_manual` | `simulation` |
`exchange`. Feature 009 writes only `local_manual`. UI labels local/manual,
never “XT account”. Feature 012 later upserts `exchange` rows in the **same**
table.

**Rationale**: Spec FR-001e / FR-012.

## Decision 8: Extend existing 009 code; no sim ledger migration

**Decision**: Keep `identity` helpers, allocation CRUD, funding path, fail-closed
corrupt load, Vite `/portfolio` proxy, Portfolio page shell. Change equity
formula and add holdings/valuation/snapshots. Do not rewrite Simulation/
Backtest journals.

**Rationale**: Spec FR-009; current implementation is a valid reservation
foundation.

## Decision 9: Package layout

**Decision**: Add `app/portfolio/valuation.py`; extend `repository.py` /
`service.py` / `api/portfolio.py`. Do not create `app/holdings`.

**Rationale**: Constitution X; spec one-book rule.
