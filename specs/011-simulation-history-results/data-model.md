# Data Model: Simulation History & Results

**Feature**: `011-simulation-history-results`  
**Date**: 2026-08-15  
**Storage**: SQLite (extend Feature 003 `simulation_sessions`)

Financial fields are decimal strings at the API; domain logic uses precise
decimals (Feature 003 money helpers).

This feature does **not** redefine Simulation Session lifecycle, Trade Journal,
or Decision Journal. Those entities remain as specified in
`specs/003-simulation-trading-core/data-model.md` (plus Feature 009/010
columns already on the session).

---

## Entity: Simulation Session (extended)

Existing row is the History list/detail identity.

| Field | Type | Notes |
|-------|------|--------|
| *(all Feature 003/005/009/010 columns)* | … | Unchanged semantics |
| `final_result_json` | TEXT \| null | Serialized **FrozenFinalResult**; null until freeze/backfill for STOPPED |

### Rules

- `CONFIGURED` / `RUNNING` / `STOPPING`: `final_result_json` MUST be null.
- `STOPPED`: `final_result_json` MUST be non-null after freeze or backfill.
- Once set, frozen metrics MUST NOT be rewritten because market prices changed.
- Backfill MAY write once when missing; MUST NOT use live/new market prices.

### Delete

- Cascade: session row + `decision_journal` rows + `trade_journal` rows for
  `session_id` (same as logical Backtest cascade).
- Reject when `state` is `RUNNING` or `STOPPING`.
- Reject when Portfolio binding still has reserved or deployed capital for this
  session (see research Decision 7).
- MUST NOT mutate Portfolio allocation/holding balances.

---

## Entity: FrozenFinalResult (embedded JSON)

Stored in `simulation_sessions.final_result_json`. One snapshot per STOPPED
session.

| Field | Type | Notes |
|-------|------|--------|
| `complete` | bool | `true` when ending equity / net P&L / return are trustworthy |
| `frozenAt` | datetime string (ISO UTC) | When snapshot was written |
| `source` | enum string | `stop` \| `recovery` \| `backfill`. **recovery** = fail-closed orphan→STOPPED + freeze; not resume/restart |
| `startingCapital` | decimal string | Copy of session starting capital at freeze |
| `endingEquity` | decimal string \| null | Authoritative terminal equity; null if incomplete |
| `netPnl` | decimal string \| null | `endingEquity − startingCapital`; null if incomplete |
| `returnPct` | decimal string \| null | `netPnl / startingCapital`; null if incomplete |
| `cash` | decimal string | Session cash at freeze |
| `fees` | decimal string | `cumulative_fees` |
| `slippageCost` | decimal string | `cumulative_slippage_cost` |
| `tradeCount` | int | |
| `strategyFillCount` | int | |
| `positionFlattenStatus` | string | Session flatten status at freeze |
| `stopReason` | string \| null | |
| `markEquity` | decimal string \| null | Optional informational; never overrides authoritative net |
| `markPrice` | decimal string \| null | Optional; only if captured at freeze time (not backfill market) |

### Completeness rules

| Situation | `complete` | `endingEquity` / `netPnl` / `returnPct` |
|-----------|------------|-------------------------------------------|
| Flat (incl. after forced close) at freeze | `true` | From `cash` vs `startingCapital` |
| Long + safe mark available **at freeze time** (`source=stop` or recovery with mark) | `true` | From Feature 003 `liquidation_equity` |
| Long without trustworthy mark (incl. `unsafe_unflattened`, ledger-only backfill while long) | `false` | `null` |
| Pre-011 backfill while flat | `true` | From persisted `cash` |
| Pre-011 backfill while long | `false` | `null` (no market fetch) |

Unverifiable metrics MUST remain null — never invent prices.

---

## Entity: HistoryListItem (API projection)

Not a table. Derived for `GET /simulation/sessions`.

| Field | Source |
|-------|--------|
| `id`, `state`, `symbol`, `timeframe`, `strategyId` | Session |
| `startedAt`, `stoppedAt`, `stopReason` | Session |
| `createdAt` | Session |
| `finalResultSummary` | Optional subset: `complete`, `netPnl`, `returnPct` when present |

Default order (locked): `created_at DESC`, then `id DESC`.

Optional filter: `state` query matching session state enum.

Pagination (API): `limit` default 50 (max 100), `offset` default 0;
list responses include `totalCount` so older sessions remain reachable.

---

## Relationships

```text
SimulationSession 1 ── * DecisionJournalEntry
SimulationSession 1 ── * TradeJournalEntry
SimulationSession 1 ── 0..1 FrozenFinalResult (embedded JSON when STOPPED)
SimulationSession 0..1 ── PortfolioAllocation (allocation_id; delete does not own it)
```

---

## State / freeze timing

```text
CONFIGURED ──start──► RUNNING ──stop/auto/recovery──► STOPPING ──► STOPPED
                                                         │
                                                         ▼
                                              persist FrozenFinalResult

STOPPED without final_result_json (legacy) ──backfill──► STOPPED + JSON
```

Illegal: overwrite a complete freeze with later live marks.  
Illegal: backfill using Feature 002 quotes.

---

## Validation summary

- Freeze helper validates decimal serialization and completeness consistency
  (`complete=true` ⇒ ending/net/return non-null; `complete=false` ⇒ those null).
- Delete eligibility computed before cascade; Portfolio unchanged on reject or
  success.
- List/detail MUST NOT fabricate journal rows (including HOLD under
  `important_only`). Detail MUST expose effective `decision_log_mode`.
