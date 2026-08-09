# Data Model: Simulation Trading Core

**Feature**: `003-simulation-trading-core`  
**Date**: 2026-08-09  
**Storage**: SQLite (see [research.md](./research.md) Decisions 6–7)

Financial fields are stored/returned as decimal strings at the API; backend
domain logic uses precise decimals.

---

## Entity: SimulationSession

One bounded simulated trading run. At most one session may be in `RUNNING` or
`STOPPING` at a time.

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | Primary key |
| `mode` | enum | Always `simulation` for creatable rows |
| `state` | enum | `CONFIGURED` \| `RUNNING` \| `STOPPING` \| `STOPPED` |
| `symbol` | string | e.g. `btc_usdt` (Feature 002 symbol) |
| `timeframe` | enum | `15m` \| `1h` \| `4h` \| `1d` (session strategy candle TF) |
| `starting_capital` | decimal string | Initial cash; start equity |
| `allocated_capital` | decimal string | Session bound; v1 MAY equal starting |
| `max_position_size` | decimal string | USDT notional cap |
| `target_net_profit` | decimal string | Stop when NET ≥ this |
| `max_session_loss` | decimal string | Positive magnitude; stop when NET ≤ −this |
| `max_trades` | int | Max simulated fills (incl. forced close) |
| `duration_seconds` | int | Session length bound |
| `fee_rate` | decimal string | Fraction, default `0.001` |
| `slippage_rate` | decimal string | Fraction, default `0.0005` |
| `strategy_id` | string | Fixed `dual_ema_9_21` for Feature 003 |
| `cash` | decimal string | Current simulated cash |
| `position_side` | enum | `flat` \| `long` |
| `position_qty` | decimal string | `0` when flat |
| `entry_ref_price` | decimal string \| null | Set when long |
| `entry_fill_price` | decimal string \| null | |
| `entry_fee` | decimal string \| null | |
| `entry_slippage_cost` | decimal string \| null | |
| `cost_basis` | decimal string \| null | Cash outlay for open long |
| `trade_count` | int | Fills so far |
| `cumulative_fees` | decimal string | |
| `cumulative_slippage_cost` | decimal string | |
| `cumulative_gross_realized` | decimal string | |
| `last_processed_candle_open_time` | int \| null | Epoch ms; duplicate guard |
| `started_at` | datetime \| null | UTC; set on RUNNING |
| `stopped_at` | datetime \| null | |
| `stop_reason` | enum \| null | See research Decision 5 |
| `position_flatten_status` | enum | `flat` \| `forced_closed` \| `unsafe_unflattened` \| `n/a` (never opened) |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### Validation (create / start)

- All FR-005 bounds present and numerically valid (positive capital, max size,
  targets/loss ≥ 0 as specified, max_trades ≥ 1, duration_seconds ≥ 1).
- `fee_rate` / `slippage_rate` ≥ 0 when provided; else defaults.
- `symbol` must be a supported Feature 002 USDT pair at start time (fail if
  unavailable — do not invent).
- `mode` must be `simulation`.
- Start rejected if another session is `RUNNING` or `STOPPING`.

### State transitions

See [research.md](./research.md) Decision 5. Illegal transitions MUST raise /
reject at the service layer.

---

## Entity: StrategySignal (ephemeral)

Not necessarily persisted as its own table; embedded in Decision Journal.

| Field | Type | Notes |
|-------|------|--------|
| `side` | enum | `BUY` \| `SELL` \| `HOLD` |
| `candle_open_time` | int | Epoch ms of evaluated closed candle |
| `fast_ema` | decimal string | |
| `slow_ema` | decimal string | |
| `strategy_id` | string | `dual_ema_9_21` |

---

## Entity: DecisionJournalEntry

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | |
| `session_id` | FK | |
| `created_at` | datetime | Clock time |
| `candle_open_time` | int \| null | Null for non-candle forced decisions if any |
| `signal` | enum | `BUY` \| `SELL` \| `HOLD` |
| `outcome` | enum | `hold` \| `approved` \| `rejected` \| `forced` |
| `reason_code` | string \| null | e.g. `conflicting_position_state`, `stale_market_data`, `warmup`, `hard_stop_flatten` |
| `reason_message` | string \| null | Human-readable |
| `fast_ema` | decimal string \| null | |
| `slow_ema` | decimal string \| null | |

**Rules**: Every closed-candle evaluation produces one row (including HOLD).
Rejected and approved non-HOLD rows required. Forced flatten SHOULD add a
`forced` row.

---

## Entity: TradeJournalEntry

| Field | Type | Notes |
|-------|------|--------|
| `id` | UUID string | |
| `session_id` | FK | |
| `created_at` | datetime | |
| `symbol` | string | |
| `side` | enum | `BUY` \| `SELL` |
| `qty` | decimal string | |
| `reference_price` | decimal string | Safe quote last used |
| `fill_price` | decimal string | After adverse slippage |
| `fee` | decimal string | |
| `slippage_cost` | decimal string | |
| `notional` | decimal string | `qty * fill_price` |
| `cash_delta` | decimal string | Signed effect on cash |
| `is_forced_close` | bool | True for hard-stop flatten |
| `candle_open_time` | int \| null | Signal candle if applicable |

**Rules**: Every simulated fill inserts exactly one row, including forced
closes. No row without an actual simulation engine fill.

---

## Entity: SessionEconomics (derived view)

Not a table — computed from session + optional safe mark:

| Field | Rule |
|-------|------|
| `startEquity` | `starting_capital` |
| `cash` | session cash |
| `equity` | cash (+ `qty * P_mark` if long and safe) |
| `grossPnl` | realized gross + unrealized gross when computable |
| `fees` | `cumulative_fees` |
| `slippageCost` | `cumulative_slippage_cost` |
| `netPnl` | `equity - startEquity` when equity computable; else null + unsafe flag |
| `tradeCount` | `trade_count` |
| `position` | side/qty/entry fields |
| `markPrice` | safe last or null |
| `markSafe` | bool |

---

## Relationships

```text
SimulationSession 1──* DecisionJournalEntry
SimulationSession 1──* TradeJournalEntry
```

---

## Position model invariants

- `position_side = flat` ⇒ `position_qty = 0` and entry fields null.
- `position_side = long` ⇒ `position_qty > 0` and entry fields set.
- No short. No partial qty changes except full open / full close.
- `trade_count` increments by 1 per Trade Journal insert.

---

## Recovery fields

On startup recovery to `STOPPED` / `backend_restart`: if `position_side=long`,
set `position_flatten_status=unsafe_unflattened` and leave qty/cash unchanged
(inspectable). Worker MUST NOT resume.
