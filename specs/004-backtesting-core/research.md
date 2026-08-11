# Research: Backtesting Core

**Feature**: `004-backtesting-core`  
**Date**: 2026-08-11  
**Status**: Complete — all Technical Context unknowns resolved

Clarifications from Session 2026-08-11 (spec.md) are treated as fixed
requirements. This document records implementation decisions that were
deferred or open at plan time.

---

## Decision 1: Shared strategy / controller / risk / accounting — backtest execution adapter

**Decision**: Reuse Feature 003 **Dual EMA**, **Trading Controller**, **Risk
Manager**, **accounting**, **position sizing**, and **money** modules without
forks. Do **not** reuse the live simulation execution path for fills. Feature
004 owns a **HistoricalExecutionAdapter** that applies next-open / end-close
fill timing, fee/slippage, and balance updates for approved orders only.

Pipeline:

```text
Historical candles → Dual EMA → Controller → Risk → HistoricalExecutionAdapter → Accounting
```

**Rationale**: Semantic parity on authority and money; fill timing differs from
live quotes, so a dedicated historical adapter avoids contaminating simulation
execution and makes “approved but unexecutable” explicit (Decision 11).

**Alternatives considered**:
- Copy Dual EMA / risk into `backtest/` — rejected (drift).
- Reuse live `execution.simulation` with patched prices — rejected (couples
  live session semantics to historical timing).
- Parameterize EMA periods in v1 — rejected (fixed 9/21).

---

## Decision 2: Fill engine — next-open / end-close

**Decision**: Chronological engine + HistoricalExecutionAdapter:

1. Process only **closed** candles in ascending time order; each candle once.
2. On closed Candle **N**, evaluate Dual EMA → Controller → Risk (Feature 003
   semantics: long-only, full position, capital nesting, optional
   `max_trades`, optional profit/loss early exits).
3. If Risk **approves**, HistoricalExecutionAdapter attempts fill at Candle
   **N+1 open** with fee + adverse slippage (shared money helpers).
4. If N+1 does not exist → **no** fill; journal `approved_unexecutable` /
   `no_next_candle` (Decision 11) — **not** a risk rejection.
5. At run end, if a long remains open → flatten at **final processed closed
   candle close** + fee + adverse slippage via the same adapter.
6. Early-exit liquidation uses the same liquidation-consistent mark rules as
   Feature 003 (aligned with equity used for drawdown).

**Rationale**: Matches locked clarification; isolates timing in the historical
adapter without changing strategy/controller/risk semantics.

**Alternatives considered**:
- Fill at Candle N close — rejected (clarification locked next-open).
- Assume infinite next candle — rejected (invents data; violates fail-safe).
- Treat missing N+1 as `rejected` — rejected (Decision 11).
---

## Decision 3: Historical candle fetch via Feature 002 boundary

**Decision**: Extend the normalized market-data API (service + adapter) to
support optional `start_time` / `end_time` (UTC ms) plus pagination until the
window is covered or empty. XT Spot kline `startTime`/`endTime` (and paging)
live **only** in `xt_spot` adapter. Backtest domain requests normalized
`Candle` lists only — never XT interval strings or raw XT payloads.

Pre-run validation:
1. Estimate bar count from `(end - start) / interval_ms`.
2. If estimate **or** a pre-accept size check shows closed-candle count would
   exceed caps (Decision 4) → **reject** with `oversized_history` and **no**
   BacktestRun row (no silent truncation).
3. After accept/`running`, if fetch yields empty series or **fewer than 21**
   closed candles → persist `failed` with `insufficient_history` (no invented
   bars). On windows with ≥21 closed candles, Dual EMA warm-up produces HOLD
   on early candles until ready (Decision 4).

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
| Warm-up / min length | Fetched window with **fewer than 21** closed candles → fail `insufficient_history`. Windows with **≥ 21** closed candles: process chronologically; early candles before Dual EMA is ready produce **HOLD** until ready (no invented prior bars). |

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

**Decision**: **Confirmed for v1.** At most **one** backtest in `running`
state. `POST /backtest/runs` validates, marks running, executes the engine
**synchronously** in the request under the 5000-candle cap, then persists as
`completed` or `failed` and returns the run. Concurrent start while one is
running → **409 Conflict**. No async worker / progress WebSocket in v1.

**Rationale**: Local single-operator; avoids forbidden WebSockets; keeps
determinism tests simple. 5000 bars of EMA + fills is well within tens of
seconds on a laptop.

**Alternatives considered**:
- Always-async worker + poll — deferred past v1 unless sync proves too slow.
- Parallel runs — rejected (spec: one in-flight).

---

## Decision 6: Persistence — SQLite, FIFO 20 completed + FIFO 5 failed

**Decision**: Store runs in SQLite under `backend/data/` (same settings pattern
as Feature 003; may share engine or use `BACKTEST_DB_PATH`). Tables:

- `backtest_runs` — id, status, config, summary, timestamps, error
- `backtest_trades` — FK run_id
- `backtest_decisions` — FK run_id

**Completed retention** (deterministic):

- Only `status = completed` counts toward the limit.
- Max **20** completed runs.
- On new completion that would exceed 20: delete the **oldest** completed
  run(s) by `completed_at` ascending (then `id` ascending as tie-break) and
  cascade children until ≤20.

**Failed retention** (deterministic — locked):

- Only `status = failed` counts toward this limit (separate from completed).
- Max **5** failed runs (`MAX_FAILED_BACKTEST_RUNS = 5`).
- On new failure that would exceed 5: delete the **oldest** failed run(s) by
  `completed_at` ascending (fallback `created_at`, then `id`) and cascade.
- Failed runs do **not** count toward the 20 completed quota.

**When a row is created (locked)**:

- Pre-run validation failures (`invalid_config`) and oversized-history
  rejection (`oversized_history`, including estimate / pre-accept size checks)
  MUST create **no** BacktestRun row and MUST NOT consume failed retention.
- Once a run is **accepted** and enters `running`, a durable row exists.
  Downstream **fetch** or **execution** failures MUST persist `status=failed`
  (including empty series and fewer than 21 closed candles →
  `insufficient_history`; market transport failures → `market_data_unavailable`
  or equivalent). Those failed rows consume the FIFO-5 quota.

Survive backend restart via SQLite. List / get / delete endpoints.

**Rationale**: Spec requires 20 completed; failed inspectability needs a fixed
cap so retention is reproducible in tests (no “opportunistic” time-based
pruning). Persistence rules keep validation noise out of history while
preserving post-accept failures for operator diagnosis.

**Alternatives considered**:
- In-memory only — rejected (must survive restart).
- Unlimited / time-based failed prune — rejected (non-deterministic).
- Failed count toward 20 — rejected (would evict successful evidence unfairly).
- Post-accept failure with no durable row — rejected (operator cannot inspect).
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
| Buy-and-hold | Cost-aware long over the **requested window**, **independent of Dual EMA warm-up**. Entry at the first **executable** price in the window: open of the candle after the first closed candle in the loaded window when that next candle exists; otherwise that first closed candle’s close. Exit at last processed closed candle’s close. Same fee + adverse slippage once on entry and once on exit. Sizing: full affordable from starting capital subject to nesting caps (same formula as a full BUY). |

**Rationale**: Locks per-candle equity for drawdown; B&H is a window baseline,
not a strategy-warmed path — delaying entry until EMA warm-up would understate
the hold period vs the configured window.

**Alternatives considered**:
- B&H entry only after EMA warm-up — rejected (user lock: independent of warm-up).
- Mark-to-market mid without fees — rejected (must match liquidation economics).
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

## Decision 11: Decision outcomes — risk rejection vs approved-but-unexecutable

**Decision**: Journal outcomes MUST distinguish controller/risk denial from
historical non-execution after approval:

| `outcome` | Meaning |
|-----------|---------|
| `hold` | Strategy HOLD; no order path |
| `approved` | Controller + Risk approved **and** HistoricalExecutionAdapter executed a fill |
| `approved_unexecutable` | Controller + Risk approved, but adapter could not fill (no Candle N+1 open). `reason_code` MUST be `no_next_candle`. **No** balance change. MUST NOT use `rejected`. |
| `rejected` | Controller or Risk denied the order (e.g. conflicting position, max_trades, sizing, capital). `reason_code` names the risk/control rule. |
| `forced` | End-of-run or early-exit flatten path |

**Rationale**: Operators and tests must not confuse “risk said no” with “risk
said yes but history had no next open.”

**Alternatives considered**:
- Map missing N+1 to `rejected` / `no_next_candle` — rejected (collapses meanings).
- Silent skip with no journal row — rejected (traceability).

---

## Resolved NEEDS CLARIFICATION checklist

| Item | Resolution |
|------|------------|
| Exact max candle / span caps | Decision 4 — 5000 bars + estimate reject |
| Range fetch approach | Decision 3 — Feature 002 + XT adapter paging |
| Sync vs async run | Decision 5 — sync under 5000, one in-flight (confirmed) |
| DB layout / retention | Decision 6 — FIFO 20 completed + FIFO 5 failed; no row on pre-accept validation/oversize; durable failed after accept |
| Metric formulas / B&H | Decision 7 — B&H independent of EMA warm-up |
| UI host | Decision 8 — Auto Trading |
| Shared vs forked modules | Decision 1 — shared strategy/control/risk/accounting; historical execution adapter |
| Fill timing | Decision 2 (spec locked) |
| Approved vs unexecutable | Decision 11 |
| Warm-up / min candles | Decision 4 — fewer than 21 → `insufficient_history`; ≥21 → HOLD until ready |

No remaining `NEEDS CLARIFICATION` items for Phase 1 design.
