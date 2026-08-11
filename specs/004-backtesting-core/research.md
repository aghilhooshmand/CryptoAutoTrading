# Research: Backtesting Core

**Feature**: `004-backtesting-core`  
**Date**: 2026-08-11  
**Status**: Complete — all Technical Context unknowns resolved

Clarifications from Session 2026-08-11 (spec.md) are treated as fixed
requirements. This document records implementation decisions that were
deferred or open at plan time.

---

## Decision 1: Shared Dual EMA — no fork

**Decision**: Import and call the existing Feature 003 Dual EMA(9)/EMA(21)
module (`backend/app/simulation/strategy/dual_ema.py` or equivalent). Backtest
must not ship a second EMA implementation.

**Rationale**: Spec FR and constitution XI require conventional Dual EMA only;
duplicate code would drift and break “same strategy as simulation.”

**Alternatives considered**:
- Copy Dual EMA into `backtest/` — rejected (drift risk).
- Parameterize periods in v1 — rejected (out of scope; fixed 9/21).

---

## Decision 2: Fill engine — next-open / end-close

**Decision**: Implement a dedicated backtest engine chronologically:

1. Process only **closed** candles in ascending time order; each candle once.
2. On closed Candle **N**, evaluate Dual EMA → Controller → Risk (Feature 003
   semantics: long-only, full position, capital nesting, optional
   `max_trades`, optional profit/loss early exits).
3. If a strategy order is **approved**, queue fill at Candle **N+1 open** with
   fee + adverse slippage (same Decimal money helpers as Feature 003).
4. If N+1 does not exist → **no** normal strategy fill.
5. At run end, if a long remains open → flatten at **final processed closed
   candle close** + fee + adverse slippage.
6. Early-exit liquidation uses the same liquidation-consistent mark rules as
   Feature 003 (aligned with equity used for drawdown).

**Rationale**: Matches locked clarification; isolates timing differences from
live simulation (which fills on live quotes) without changing strategy/
controller semantics.

**Alternatives considered**:
- Fill at Candle N close — rejected (clarification locked next-open).
- Assume infinite next candle — rejected (invents data; violates fail-safe).

---

## Decision 3: Historical candle fetch via Feature 002 boundary

**Decision**: Extend the normalized market-data API (service + adapter) to
support optional `start_time` / `end_time` (UTC ms) plus pagination until the
window is covered or empty. XT Spot kline `startTime`/`endTime` (and paging)
live **only** in `xt_spot` adapter. Backtest domain requests normalized
`Candle` lists only — never XT interval strings or raw XT payloads.

Pre-run validation:
1. Estimate bar count from `(end - start) / interval_ms`.
2. If estimate **or** fetched closed-candle count exceeds caps (Decision 4) →
   **reject** with clear error (no silent truncation).
3. If after fetch the closed series is empty / insufficient for Dual EMA warm-up
   → reject / fail safely (no invented bars).

**Rationale**: Constitution XVI–XVIII and Feature 002 boundary; XT already
supports ranged klines; current limit-only API is insufficient for arbitrary
windows.

**Alternatives considered**:
- Client-only `limit` chunks without range — rejected (cannot express arbitrary
  historical windows reliably).
- Third-party candle CDN — rejected (extra dependency; out of constitution
  adapter model).

---

## Decision 4: History size caps (exact numbers)

**Decision**: Enforce **both** a hard candle count and a soft span check:

| Constraint | Value |
|------------|-------|
| `MAX_BACKTEST_CANDLES` | **5000** closed candles per run (all intervals) |
| Pre-fetch estimate reject | If `(end_ms - start_ms) / interval_ms > 5000` → HTTP 400 before fetch |
| Post-fetch reject | If closed candles in window > 5000 → HTTP 400 (no truncate) |
| Warm-up | Dual EMA needs ≥ 21 closed closes before first cross can fire; fewer closed candles → fail with clear message (not silent empty results) |

Documented approximate max spans at 5000 bars (operator guidance):

| Interval | ≈ Max span at 5000 bars |
|----------|-------------------------|
| 1m | ~3.5 days |
| 5m | ~17 days |
| 15m | ~52 days |
| 1h | ~208 days |
| 4h | ~833 days (~2.3 years) |
| 1d | ~5000 days (~13.7 years) |

**Rationale**: Spec deferred exact caps to plan; 5000 balances XT page loops,
local sync run time, and SQLite journal size. Single global count keeps rules
simple (constitution X).

**Alternatives considered**:
- Per-interval different max counts — deferred (more UI/docs complexity).
- Silent truncate to last N — rejected (clarification: reject oversized).
- Unlimited history — rejected (operator machine / API abuse risk).

---

## Decision 5: One in-flight run; synchronous execution under cap

**Decision**: At most **one** backtest in `running` state. `POST /backtest/runs`
validates, marks running, executes the engine **synchronously** in the request
(≤5000 candles is CPU-light for Dual EMA), then persists as `completed` or
`failed` and returns the run summary. Concurrent start while one is running →
**409 Conflict**.

**Rationale**: Local single-operator; avoids WebSocket progress channels
(forbidden); keeps determinism tests simple. 5000 bars of EMA + fills is well
within tens of seconds on a laptop.

**Alternatives considered**:
- Always-async worker + poll — more moving parts; defer unless sync proves too
  slow in practice.
- Parallel runs — rejected (spec: one in-flight).

---

## Decision 6: Persistence — SQLite, FIFO 20 completed runs

**Decision**: Store completed (and failed) runs in SQLite under `backend/data/`
(same settings pattern as Feature 003; may share engine or use
`BACKTEST_DB_PATH` defaulting beside simulation DB). Tables:

- `backtest_runs` — id, status, config JSON, summary JSON, timestamps, error
- `backtest_trades` — FK run_id, trade journal rows
- `backtest_decisions` — FK run_id, decision journal rows

Retention: when saving a new **completed** run would exceed **20** completed
runs, delete the **oldest** completed run(s) and cascaded children until ≤20.
Failed runs: keep latest failed for inspect, but only **completed** count
toward the 20; optionally prune old failed beyond a small bound (e.g. keep
last 5 failed) — implementers may keep failed outside the 20 if documented;
**preferred**: only completed count toward 20; delete oldest completed on
overflow; failed runs older than 7 days may be deleted opportunistically.

Survive backend restart via SQLite file. List / get / delete endpoints.

**Rationale**: Matches clarification; Feature 003 already uses SQLAlchemy +
SQLite; no new DB product.

**Alternatives considered**:
- In-memory only — rejected (must survive restart).
- Unlimited history — rejected (clarification: 20).

---

## Decision 7: Metrics definitions

**Decision**:

| Metric | Definition |
|--------|------------|
| Net P&L | Ending equity − starting capital (liquidation-consistent; fees & slippage included) |
| Return % | `net_pnl / starting_capital` (Decimal; expose as string in API) |
| Trade stats | Count of closed round-trips; wins = round-trip net P&L > 0; losses ≤ 0 as specified in data-model |
| Win rate | wins / closed round-trips (0 if none) |
| Total fees / slippage | Sum from trade journal |
| Max drawdown | From equity series recorded **after every processed closed candle** (liquidation-consistent mark); peak-to-trough absolute and % of peak |
| Best / worst trade | Max / min round-trip net P&L |
| Buy-and-hold | Buy at first available fill-style open after warm-up aligned with next-open rule (or first N+1 open in series used for strategy); sell at final processed close; apply same fee + adverse slippage model; report net P&L and return % |

**Rationale**: Locks clarification on per-candle equity for drawdown; keeps
B&H cost-aware and comparable to strategy path.

**Alternatives considered**:
- Mark-to-market mid without fees for equity — rejected (must match liquidation).
- B&H without fees — rejected (spec: cost-aware).

---

## Decision 8: UI placement

**Decision**: Add Backtest configure / run / list / inspect under **Auto
Trading** (section or tab alongside simulation). Do **not** add a fourth
primary nav item. Phone-width (~375px) primary path: configure → run → see
summary → open trades/decisions.

**Rationale**: Constitution XIII; Feature 003 already owns Auto Trading.

**Alternatives considered**: Separate top-level Backtest page — rejected.

---

## Decision 9: Isolation from live simulation

**Decision**: Backtest uses ephemeral in-memory session state for the engine
run; it must **not** read or write Feature 003 live simulation session tables /
worker state. Market-data fetches may share the Feature 002 client (rate
limits apply). Simulation may remain active during a backtest.

**Rationale**: Spec isolation requirement; reduces corruption risk.

**Alternatives considered**: Shared mutable session singleton — rejected.

---

## Decision 10: API shape

**Decision**: REST under `/backtest` (see `contracts/backtest-api.md`):

- `POST /backtest/runs` — start (sync complete)
- `GET /backtest/runs` — list summaries (newest first)
- `GET /backtest/runs/{id}` — config + summary + optional include
- `GET /backtest/runs/{id}/trades`
- `GET /backtest/runs/{id}/decisions`
- `DELETE /backtest/runs/{id}`

Money fields as Decimal strings. Errors use existing API error envelope
(`code`, `message`, optional `details`).

**Rationale**: Matches Feature 003 API style; inspectable journals without WS.

---

## Resolved NEEDS CLARIFICATION checklist

| Item | Resolution |
|------|------------|
| Exact max candle / span caps | Decision 4 — 5000 bars + estimate reject |
| Range fetch approach | Decision 3 — Feature 002 + XT adapter paging |
| Sync vs async run | Decision 5 — sync, one in-flight |
| DB layout / retention | Decision 6 — SQLite FIFO 20 completed |
| Metric formulas | Decision 7 |
| UI host | Decision 8 — Auto Trading |
| Strategy reuse | Decision 1 |
| Fill timing | Decision 2 (spec locked) |

No remaining `NEEDS CLARIFICATION` items for Phase 1 design.
