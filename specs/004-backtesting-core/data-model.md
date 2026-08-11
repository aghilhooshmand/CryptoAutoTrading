# Data Model: Backtesting Core

**Feature**: `004-backtesting-core`  
**Date**: 2026-08-11  
**Storage**: SQLite (see [research.md](./research.md) Decision 6)

Financial fields are stored/returned as decimal strings at the API; backend
domain logic uses precise decimals (same money helpers as Feature 003).

---

## Entity: BacktestRun

One bounded historical evaluation. At most one run may be `running` at a time
(v1). Completed runs are retained (max **20**); oldest completed evicted on
overflow.

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | Primary key |
| `status` | enum | `pending` \| `running` \| `completed` \| `failed` |
| `symbol` | string | e.g. `btc_usdt` (Feature 002) |
| `timeframe` | enum | `1m` \| `5m` \| `15m` \| `1h` \| `4h` \| `1d` |
| `start_time` | int | Window start UTC epoch ms (inclusive intent) |
| `end_time` | int | Window end UTC epoch ms |
| `starting_capital` | decimal string | Initial cash |
| `allocated_capital` | decimal string | Deploy cap for full BUY |
| `max_position_size` | decimal string | Additional USDT notional cap |
| `target_net_profit_rate` | decimal string \| null | Optional; fraction of allocated |
| `max_session_loss_rate` | decimal string \| null | Optional; fraction of allocated |
| `target_net_profit_amount` | decimal string \| null | Derived when rate set |
| `max_session_loss_amount` | decimal string \| null | Derived when rate set |
| `max_trades` | int \| null | Optional; strategy fills only |
| `fee_rate` | decimal string | Default `0.001` |
| `slippage_rate` | decimal string | Default `0.0005` |
| `strategy_id` | string | Always `dual_ema_9_21` |
| `error_code` | string \| null | When `failed` |
| `error_message` | string \| null | Human-readable |
| `candle_count` | int \| null | Closed candles processed (completed) |
| `created_at` | datetime | UTC |
| `started_at` | datetime \| null | |
| `completed_at` | datetime \| null | |
| `summary` | BacktestSummary \| null | Embedded or 1:1; required when completed |

### Validation (create / run)

- Capital invariant: `0 < max_position_size ≤ allocated_capital ≤ starting_capital`.
- `end_time > start_time`.
- `timeframe` in supported set; `symbol` supported by Feature 002 at run time.
- History size: estimated bars and fetched closed count ≤ `MAX_BACKTEST_CANDLES`
  (**5000**); else reject (`oversized_history`) before processing.
- `max_trades` if present: integer ≥ 1.
- Profit/loss rates if present: > 0; derive absolute amounts from allocated.
- `fee_rate` / `slippage_rate` ≥ 0 when provided; else Feature 003 defaults.
- Reject if another run is `running` (`409` / `backtest_already_running`).
- Insufficient closed candles for Dual EMA warm-up → fail safely
  (`insufficient_history`); do not invent bars.

### State transitions

```text
(create+execute) → running → completed
                         ↘ failed
```

Illegal concurrent start while `running` → reject. Completed/failed are
terminal. Delete removes the row and cascaded journals.

### Retention

- At most **20** rows with `status = completed`.
- On new completion that would exceed 20: delete oldest completed (by
  `completed_at`) and cascaded trades/decisions.
- Failed runs do not count toward 20; keep a small recent failed set for
  inspect (implementation may prune opportunistically).

---

## Entity: BacktestConfiguration

Operator inputs that fully determine a run when combined with a fixed candle
series. Stored as fields on `BacktestRun` (not a separate table required).

| Field | Required | Notes |
|-------|----------|--------|
| symbol, timeframe, start/end | yes | |
| starting / allocated / max position | yes | Nesting invariant |
| fee_rate, slippage_rate | no | Defaults apply |
| max_trades | no | Null = uncapped |
| target_net_profit_rate | no | Null = no early profit exit |
| max_session_loss_rate | no | Null = no early loss exit |

---

## Entity: HistoricalCandleSeries (ephemeral)

Ordered closed OHLC from Feature 002 for the window. Not persisted as its own
table (reproducibility relies on exchange history + stored config; fixtures
used in tests).

| Field | Type | Notes |
|-------|------|--------|
| candles | list[Candle] | Normalized; ascending `open_time` |
| Each candle | open, high, low, close, volume, open_time, close_time, is_closed | Only `is_closed=true` processed |

**Rules**: Chronological; each candle identity at most once; no fabricated gaps.

---

## Entity: StrategySignal (ephemeral)

From **shared** Dual EMA(9)/EMA(21); advisory only.

| Field | Type | Notes |
|-------|------|--------|
| `side` | enum | `BUY` \| `SELL` \| `HOLD` |
| `candle_open_time` | int | Signal candle N |
| `fast_ema` / `slow_ema` | decimal string | |
| `strategy_id` | string | `dual_ema_9_21` |

---

## Entity: BacktestDecisionRecord

One row per processed closed candle (and forced/end flatten decisions).

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | |
| `run_id` | FK → BacktestRun | |
| `created_at` | datetime | |
| `candle_open_time` | int \| null | |
| `signal` | enum | `BUY` \| `SELL` \| `HOLD` |
| `outcome` | enum | `hold` \| `approved` \| `rejected` \| `forced` |
| `reason_code` | string \| null | e.g. `conflicting_position_state`, `no_next_candle`, `max_trades`, `warmup`, `end_of_run_flatten`, `profit_target`, `max_loss` |
| `reason_message` | string \| null | |
| `fast_ema` / `slow_ema` | decimal string \| null | |

**Rules**: HOLD produces a row with no balance change. Approved strategy
non-HOLD with no N+1 → record rejection/skip with `no_next_candle` (no fill).
End-of-run flatten SHOULD add `forced` / end-of-run reason.

---

## Entity: BacktestTrade

Deterministic simulated fill; never a real order.

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | |
| `run_id` | FK | |
| `created_at` | datetime | |
| `side` | enum | `BUY` \| `SELL` |
| `qty` | decimal string | |
| `reference_price` | decimal string | N+1 open or final close |
| `fill_price` | decimal string | After adverse slippage |
| `fee` | decimal string | |
| `slippage_cost` | decimal string | |
| `notional` | decimal string | |
| `signal_candle_open_time` | int \| null | Candle N for strategy fills |
| `fill_candle_open_time` | int | Candle used for price |
| `is_end_of_run_flatten` | bool | True for final-close flatten |
| `is_forced_close` | bool | Early-exit / flatten path (align with 003 naming) |
| `round_trip_id` | UUID string \| null | Links entry+exit for P&L stats |

**Fill rules**:

- Strategy approved on Candle N → reference = Candle N+1 **open**; if missing →
  no trade.
- End-of-run / early-exit flatten while long → reference = final processed
  closed candle **close**; exactly one such flatten when needed.
- Fee/slippage: same Feature 003 adverse model.

---

## Entity: EquityPoint (ephemeral during run; optional persist)

| Field | Type | Notes |
|-------|------|--------|
| `candle_open_time` | int | After processing this closed candle |
| `equity` | decimal string | Liquidation-consistent (cash if flat; liquidation equity if long) |

**Rules**: One point after **every** processed closed candle. Max drawdown is
computed **only** from this series (peak-to-trough). Persistence of the full
series is optional for v1; summary must store computed max drawdown absolute
and percent.

---

## Entity: BacktestSummary

Stored with completed run (JSON column or 1:1 table).

| Field | Type | Notes |
|-------|------|--------|
| `starting_capital` | decimal string | |
| `ending_capital` | decimal string | After final flatten if any |
| `net_pnl` | decimal string | ending − starting |
| `return_pct` | decimal string | net_pnl / starting_capital |
| `trade_count` | int | Fill count (legs) |
| `round_trip_count` | int | Completed entry→exit |
| `winning_trades` | int | Round-trips with net P&L > 0 |
| `losing_trades` | int | Round-trips with net P&L ≤ 0 |
| `win_rate` | decimal string | wins / round_trips; `0` if none |
| `total_fees` | decimal string | |
| `total_slippage` | decimal string | |
| `max_drawdown` | decimal string | Absolute peak-to-trough |
| `max_drawdown_pct` | decimal string | Relative to peak equity |
| `best_trade` | decimal string \| null | Best round-trip net; null if none |
| `worst_trade` | decimal string \| null | Worst round-trip net; null if none |
| `buy_and_hold_net_pnl` | decimal string | Cost-aware B&H |
| `buy_and_hold_return_pct` | decimal string | |
| `strategy_fill_count` | int | Strategy-driven fills (excludes flatten) |

### Buy-and-hold (FR-017)

- Entry reference: open of the candle **after** the first usable closed candle
  in range when a next candle exists; else that candle’s close.
- Exit reference: last processed closed candle’s close.
- Apply fee + adverse slippage once on entry and once on exit.
- Same capital notionals as a single full long sized like Feature 003 from
  starting cash / allocated / max position (document which sizing B&H uses —
  **preferred**: full affordable from starting capital subject to nesting caps,
  identical to first possible full BUY sizing at start).

### Round-trip win/loss (FR-020)

Completed round-trip = entry BUY fill through full exit SELL (strategy or
end-of-run flatten). Stats use round-trip net P&L, not single legs alone.

---

## Relationships

```text
BacktestRun 1 ── * BacktestTrade
BacktestRun 1 ── * BacktestDecisionRecord
BacktestRun 1 ── 1 BacktestSummary (when completed)
```

Live Feature 003 `SimulationSession` is **not** related; no shared mutable
session state.

---

## Isolation rules

- Backtest engine uses ephemeral in-run cash/position state.
- MUST NOT mutate simulation session tables, worker, or live balances.
- Market data via Feature 002 only; no XT types in this model.
