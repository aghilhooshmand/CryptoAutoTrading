# Research: Strategy Comparison and Evaluation

**Feature**: `007-strategy-comparison`  
**Date**: 2026-08-12  
**Spec**: [spec.md](./spec.md)

## Decision 1: Orchestrator reuses `run_engine` with one candle fetch

**Decision**: Implement a comparison service that validates shared config once,
validates each of 2–5 legs via `validate_and_materialize`, fetches candles
**once**, then for each leg creates a `BacktestRunRow` and calls existing
`run_engine(db, run_id, shared_candles, ...)`. Extract a helper from
`backtest/service.py` for “run with prefetched candles” if needed so legs do
not re-fetch.

**Rationale**: FR-003/FR-005 require identical series and Feature 004 semantics.
Refetching per leg risks drift and waste.

**Alternatives considered**:
- N independent `POST /backtest/runs` from the client — rejected (no shared
  series guarantee; race with `backtest_already_running`; weaker fairness).
- Fork a comparison-only evaluator — rejected (constitution X / FR-005).

## Decision 2: Persist legs as normal backtests with `origin=comparison`

**Decision**: Add `origin` on backtest runs (`manual` | `comparison`) and
optional `comparison_id` FK/link. Comparison legs always set
`origin=comparison`. `GET /backtest/runs` defaults to `origin=manual` (or
`excludeOrigin=comparison`) so history stays clean; explicit query includes
comparison legs. Drill-down uses existing `/backtest/runs/{id}` + journals.

**Rationale**: Clarify Q2 — fully inspectable normal runs, hideable from main
list.

**Alternatives considered**:
- Comparison-only storage without backtest rows — rejected (FR-007 inspect).
- Always show legs in main list — rejected (clutter; clarify Q2).

## Decision 3: Synchronous request; comparison-level concurrency lock

**Decision**: `POST /comparisons` (or equivalent) blocks until all legs finish.
Hold a **comparison-level in-flight lock** (distinct from or wrapping Feature
004’s single `running` backtest guard) so per-leg `BacktestRun` persistence
does not incorrectly raise `backtest_already_running` mid-comparison. Concurrent
second `POST /comparisons` while one is in flight → `409`. No polling, workers,
or WebSockets.

**Rationale**: Clarify Q3; Feature 004 sync precedent; research/implement task
coverage (orchestrator + contract tests).

**Alternatives considered**:
- Async comparison jobs — rejected for v1.
- Fire parallel processes — unnecessary complexity; sequential legs on shared
  candles are simpler and deterministic.

## Decision 4: Strictest `S` gate; fail-closed after accept

**Decision**: Pre-accept: reject oversized windows (Feature 004 cap). After
fetch (or on estimate): require `candle_count ≥ max(leg.min_history_candles())`.
If any leg fails after the comparison is accepted into running, mark the whole
comparison `failed` and do not return a mixed completed/failed leaderboard.

**Rationale**: Spec edge cases / FR-009; fairness.

**Alternatives considered**:
- Per-leg insufficient → skip that row — rejected (partial leaderboard).
- Use Dual EMA’s fixed 21 for all — rejected (per-strategy `S` from 005/006).

## Decision 5: Comparison metrics map from engine summary

**Decision**: Comparison table fields map from existing `summary_json` keys:

| Spec metric | Engine / derived |
|-------------|------------------|
| net P&L | `netPnl` |
| return % | `returnPct` |
| max drawdown | `maxDrawdown` / `maxDrawdownPct` (expose both or primary absolute + pct as today) |
| win rate | `winRate` |
| roundTripCount | `roundTripCount` |
| fillCount | `strategyFillCount` (API alias `fillCount` on comparison row) |
| total fees / slippage | `totalFees` / `totalSlippage` |
| best / worst trade | `bestTrade` / `worstTrade` |
| buy-and-hold return | `buyAndHoldReturnPct` (shared value across rows) |
| vs buy-and-hold | `returnPct − buyAndHoldReturnPct` (store on comparison leg summary) |

Buy-and-hold uses Feature 004 methodology; prefer computing once from shared
candles when feasible, else identical per-leg engine B&H on the same series.

**Rationale**: Clarify Q5 requires both activity metrics; avoid second ledger.

**Alternatives considered**:
- Recompute metrics outside the engine — rejected.
- Show only one of round-trip/fill — rejected (clarify Q5).

## Decision 6: Retention split

**Decision**: Comparison records: FIFO **10** completed + **5** failed.
Evicting a comparison does **not** delete its leg backtests; legs follow
Feature 004 retention (20/5) and may later dangle if a leg is FIFO-deleted
while a comparison still references it (UI shows “run unavailable”).

**Rationale**: Clarify Q4.

**Alternatives considered**:
- Cascade-delete legs when comparison evicts — rejected (clarify: legs follow
  004 independently).
- Match 20 completed comparisons — rejected (heavier; up to 5× runs each).

## Decision 7: No ranking / winner UX

**Decision**: Results table has no “best”, crown, or auto-sort-by-return as a
ranked endorsement. Optional operator-controlled column sort is allowed if it
does not label a winner. Copy must not imply guaranteed profit (constitution
XII).

**Rationale**: FR-008 / clarify intent.

**Alternatives considered**:
- Highlight max returnPct — rejected.

## Decision 8: API shape

**Decision**: New resource under `/comparisons` (or `/backtest/comparisons`):
create (sync), get, list, delete. Create body = shared Feature 004 money/window
fields + `legs: [{ strategyId, strategyParams? }]` (length 2–5). Response
includes comparison status, shared B&H, and per-leg metrics + `backtestRunId`.

**Rationale**: Clear separation from single-run create; keeps Feature 004
create unchanged.

**Alternatives considered**:
- Overloaded `POST /backtest/runs` with array of strategies — messier
  contracts and retention.
