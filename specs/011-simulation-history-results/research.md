# Research: Simulation History & Results

**Feature**: `011-simulation-history-results`  
**Date**: 2026-08-15  
**Spec**: [spec.md](./spec.md)

## Decision 1: History is inspection only (no second engine)

**Decision**: Reuse Feature 003 session + trade/decision journals as the source
of truth. Feature 011 adds list/delete, frozen terminal snapshot, and UI. Do
not re-simulate fills or maintain a parallel cash/position ledger for History.

**Rationale**: Constitution III / FR-019; roadmap architecture note.

**Alternatives considered**:
- Materialized “HistoryRun” clone of BacktestRun — rejected (duplication).
- Recompute terminal P&L from journals on every read — rejected (price drift;
  incomplete vs freeze rules).

## Decision 2: Persist freeze as JSON on the session row

**Decision**: Add `final_result_json` (TEXT) on `simulation_sessions`, same
pattern as Backtest `summary_json`. Store decimal strings and a
`complete: bool`. Optionally store `frozenAt` ISO timestamp inside the JSON.

**Rationale**: Constitution X; one row per session; no join required for list
summaries; matches existing SQLite evolution via `_ensure_column`.

**Alternatives considered**:
- Separate `simulation_final_results` table — deferred (unnecessary for 1:1).
- Many typed columns for each metric — noisier migrations for little gain.

## Decision 3: Always snapshot on STOPPED; incomplete uses nulls

**Decision**: Every path that reaches `STOPPED` writes a final-result snapshot
(operator stop, emergency stop, auto hard-stops, backend restart recovery).
When ending equity / net P&L / return cannot be trusted, set `complete: false`
and leave those fields `null`. Always persist truthful fields: starting
capital, cash, fees, slippage, trade counts, flatten status, stop reason.

**Rationale**: Clarify Q3; FR-008/FR-011.

**Alternatives considered**: Snapshot only when complete — rejected (clarify A).

## Decision 4: Authoritative terminal equity = Feature 003 Session NET basis

**Decision**: For **complete** freezes:
- If flat (including after successful forced close): ending equity = `cash`;
  net P&L = `cash − starting_capital`; return = net / starting_capital.
- If still long with a **safe mark available at freeze time**: ending equity =
  Feature 003 `liquidation_equity(...)`; net/return from that (same as live
  hard-limit Session NET). Store informational mark equity only as optional
  non-authoritative fields if useful; never substitute it for authoritative
  net P&L.

At stop after flatten, position is normally flat → cash-based complete freeze
is the common path.

**Rationale**: Spec assumptions; constitution VI; avoid inventing a new P&L
definition.

**Alternatives considered**: Always mark-to-market equity — rejected (Feature
003 hard limits use liquidation equity).

## Decision 5: Pre-011 backfill = ledger only, never live market

**Decision**: On first list/get (or explicit migration pass at startup) for
STOPPED sessions missing `final_result_json`:
- Derive from persisted session fields only (`cash`, position side/qty,
  fees, slippage, counts, flatten, stop reason, starting capital).
- **Never** call Feature 002 quotes / mark fetch for backfill.
- Flat → complete from cash.
- Long / incomplete valuation → `complete: false`, null ending equity/P&L/return.
- Idempotent: once written, never overwrite with later market data.

**Rationale**: Clarify Q1; FR-021.

**Alternatives considered**:
- Forward-only (no backfill) — rejected (operator chose B).
- Lazy freeze using current prices — rejected (falsifies history).

## Decision 6: STOPPED detail uses freeze only; RUNNING keeps live economics

**Decision**:
- `STOPPED` with `finalResult`: API and History/detail UI MUST treat
  `finalResult` as the **sole authoritative** ending economics. Do **not**
  expose current/live mark-based ending equity / net P&L / return on the
  STOPPED History detail contract in a form that can drift after termination
  (omit live mark-derived ending fields, or do not return a drifting
  `economics` block for STOPPED when `finalResult` is present).
- `RUNNING` / `STOPPING`: keep existing live economics behavior; no freeze yet.
- `CONFIGURED`: no `finalResult`.

**Rationale**: FR-010/FR-012; SC-002; analyze remediation A1.

**Alternatives considered**: Return live `economics` alongside freeze with a
label — rejected (drift risk in History contract).

## Decision 7: Delete guards (state + Portfolio binding)

**Decision**:
1. Reject delete if `state ∈ {RUNNING, STOPPING}`.
2. Reject delete if session has `allocation_id` **and** that allocation still
   holds **reserved > 0** or the session still has **binding deployed**
   (open long cost basis / Feature 009 binding deployed projection) for that
   binding.
3. Otherwise allow delete after UI confirm: cascade session row + decision
   journal + trade journal (+ final result JSON with the row).
4. Never call Portfolio release/unwind from delete.

**Rationale**: Clarify Q2; FR-014/FR-016/FR-022; capital protection.

**Alternatives considered**: Auto-unwind on delete — rejected. Allow orphan
reserved capital — rejected.

## Decision 8: API surface mirrors Backtest list/delete (with offset pagination)

**Decision**:
- `GET /simulation/sessions` — list with optional `state`; **order locked** to
  `created_at DESC, id DESC`; **offset pagination**: `limit` default **50**,
  max **100**; `offset` default **0**; response includes **`totalCount`**.
  UI MUST be able to fetch older pages — do not silently truncate History
  permanently.
- Existing `GET /simulation/sessions/{id}` — enrich with `finalResult`.
- Existing journals endpoints — unchanged.
- `DELETE /simulation/sessions/{id}` — 204 on success; structured errors for
  reject cases.
- Keep `GET /simulation/sessions/active` for reconnect.

**Rationale**: Familiar operator/API pattern from Feature 004; analyze
remediation I1/U1/U4.

**Alternatives considered**: Separate `/simulation/history` resource — rejected
(sessions already are the history). Soft limit without offset — rejected
(permanent silent truncation).

## Decision 9: Frontend UX (clarify Q4–Q5)

**Decision**:
- History **list** on Auto Trading → Simulation tab (alongside create/live).
- **Dedicated detail route locked** to `/auto-trading/simulation/:sessionId`
  (MUST NOT add a new primary nav item).
- **STOPPED**: inspect + delete confirm only — no restart / resume / run-again
  on the same historical session id.
- **CONFIGURED**: MAY use the existing Feature 003 **Start** action (reuse
  existing start path; do not create a second start implementation).
- RUNNING: continue reconnect via active session; refresh must not POST stop.
- Follow `docs/UI_UX_STANDARDS.md` (~375px, confirm destructive).

**Rationale**: Clarify C + A; FR-001/FR-023/FR-024; analyze remediation U2/U3.

**Alternatives considered**: Top-level History nav — rejected. Restart from
History — rejected. Duplicate start stack — rejected.

## Decision 10: No FIFO retention; offset pagination instead

**Decision**: Do not auto-delete oldest sessions. Operator deletes explicitly.
List uses offset pagination (`limit`/`offset`/`totalCount`) so older sessions
remain reachable — not a permanent silent truncate.

**Rationale**: Spec assumption; differs from Backtest 20/5 caps intentionally.

**Alternatives considered**: Copy Backtest FIFO — rejected. Limit-only without
offset — rejected.

## Decision 11: Freeze hook points

**Decision**: Single helper `persist_final_result(db, row, *, mark=..., safe=...)`
called from:
- `stop_session_async` after flatten + STOPPED transition
- pipeline auto-stop completion paths that set STOPPED
- `recover_orphan_sessions` after marking STOPPED

Backfill helper for missing snapshots on read/list (ledger-only).

**Terminology — recovery**: In Feature 011, **recovery** means the existing
fail-closed orphan handling (`RUNNING`/`STOPPING` → `STOPPED` on backend
restart) **plus** final-result freeze/backfill as applicable. It does **NOT**
mean resume, restart of the same session id, or worker recreation after
restart.

**Rationale**: One freeze implementation; no missed stop paths; FR-020.

**Alternatives considered**: Only freeze in HTTP stop handler — rejected
(misses auto-stop and recovery).
