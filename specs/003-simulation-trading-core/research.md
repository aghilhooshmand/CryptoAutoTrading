# Research: Simulation Trading Core

**Feature**: `003-simulation-trading-core`  
**Date**: 2026-08-09

All Technical Context unknowns and the ten explicit planning decisions are
resolved below. Locked product clarifications from `spec.md` are treated as
inputs, not reopened.

---

## Decision 1: Dual EMA periods and crossover rule

**Decision**: Use **EMA(9)** fast and **EMA(21)** slow on **closed** candle
**close** prices for the session timeframe. Signal on **cross** between the
prior closed bar and the newly closed bar:

| Condition | Signal |
|-----------|--------|
| Fast EMA crosses **from at/below to above** slow EMA | `BUY` |
| Fast EMA crosses **from at/above to below** slow EMA | `SELL` |
| Otherwise (including equal EMAs, continuation without cross) | `HOLD` |

Warm-up: require enough closed candles to seed both EMAs (at least 21 closes;
implementation MAY use the standard EMA recursive formula with SMA seed over
the first `period` closes). Until warm-up is complete, emit `HOLD` and still
write a Decision Journal entry noting `warmup` / insufficient history when an
evaluation occurs.

**Rationale**: Conventional, explainable, easy to unit-test; proves the engine
without optimizing profitability (Constitution XI + user preference).

**Alternatives considered**:
- SMA(10)/SMA(30): also fine; EMA reacts slightly faster and is equally common
  for crossover demos.
- EMA(12)/EMA(26): MACD-adjacent; slightly heavier narrative for “prove engine”.
- Optimize periods per pair: out of scope (no optimization/backtesting).

---

## Decision 2: Full position size from allocated capital

**Decision**: Feature 003 always opens **one full long** sized as:

1. Let `fee_rate` and `slippage_rate` be the session rates (defaults 0.001 and
   0.0005).
2. Let `P_ref` be the latest **safe** quote last price (Feature 002 normalized
   quote). Fail safe if unavailable/stale.
3. Adverse BUY fill price: `P_fill = P_ref * (1 + slippage_rate)`.
4. Maximum affordable notional from cash (cash must cover notional + fee):

   `affordable_notional = cash / (1 + fee_rate)`

5. Intended full notional:

   `intended_notional = min(affordable_notional, max_position_size)`

   where `max_position_size` is the configured USDT notional cap.

6. If `intended_notional <= 0` (or below a documented dust floor, e.g. notional
   that would round to zero quantity), **reject** `insufficient_balance` —
   do **not** silently shrink to a partial “almost full” size below the
   intended rule after approval.

7. Base quantity: `qty = intended_notional / P_fill` (decimal arithmetic).

8. Fill notional `N = qty * P_fill`; fee `F = N * fee_rate`; cash debit
   `N + F`; position becomes LONG with `qty` and cost basis recorded as
   `N + F` (cash outlay).

**SELL (full close)**:

1. `P_fill = P_ref * (1 - slippage_rate)` (adverse for sell).
2. `N = qty * P_fill`; `F = N * fee_rate`; cash credit `N - F`; position → FLAT.
3. Quantity closed is always the **entire** open `qty`.

**Starting vs allocated capital (v1)**: UI MAY collect a single capital figure
stored as both `starting_capital` and `allocated_capital` (equal). Session
starts flat with `cash = starting_capital`. `allocated_capital` documents the
session bound; sizing uses **current cash** and `max_position_size` as above.

**Rationale**: Matches long-only full-position model; keeps fee coverage
explicit; rejects rather than silent partials.

**Alternatives considered**:
- Always deploy 100% of starting capital ignoring max_position_size: violates
  session bound.
- Partial fills to use leftover cash dust: conflicts with “no partial silent
  oversize” / single full position simplicity.
- Size from allocated_capital even after cash reduced by fees: can overspend
  cash; rejected.

---

## Decision 3: Session equity and NET P&L formulas

All money math uses **decimals** (string I/O at API boundary; `Decimal` in
backend). Rates are fractions: `0.10% → 0.001`, `0.05% → 0.0005`.

### Per-fill economics

- **Reference price** `P_ref`: safe quote last.
- **Fill price** `P_fill`: adverse-adjusted as in Decision 2.
- **Slippage cost** (signed impact in quote currency):  
  BUY: `(P_fill - P_ref) * qty`  
  SELL: `(P_ref - P_fill) * qty`  
  (Both non-negative when slippage_rate ≥ 0.)
- **Fee**: `fee_rate * (qty * P_fill)`.
- **Gross trade P&L**: realized only on SELL vs position cost basis (see below);
  BUY realizes 0.

### Position cost basis

On BUY: `cost_basis = N + F` (total cash spent to open).  
On SELL: realized gross ≈ `(qty * P_ref) - (cost_basis - fees_already_in_basis)` —
for reporting, define:

- **Realized gross P&L** (on close): `(qty * P_ref) - entry_notional`  
  where `entry_notional` is `qty * entry_ref_price` stored at open (reference,
  pre-slippage), **or** equivalently track entry `P_ref` and qty.
- Practical v1 (deterministic, testable):

  Store on open: `qty`, `entry_ref_price`, `entry_fill_price`, `entry_fee`,
  `entry_slippage_cost`.

  On close at `exit_ref`, `exit_fill`, `exit_fee`, `exit_slippage_cost`:

  - `gross_realized = (exit_ref - entry_ref) * qty`
  - `fees_total_trade = entry_fee + exit_fee`
  - `slippage_total_trade = entry_slippage_cost + exit_slippage_cost`
  - `net_realized = gross_realized - fees_total_trade - slippage_total_trade`

  This equals cash delta for a round trip when mark-ups match fill math.

### Session aggregates

- `start_equity = starting_capital` (session starts flat).
- `cash` = running simulated cash.
- If FLAT: `equity = cash`.
- If LONG and **safe** mark `P_mark` available:  
  `equity = cash + qty * P_mark`  
  (mark uses safe last price **without** applying slippage — valuation, not
  execution).
- If LONG and **no** safe mark: equity / unrealized / Session NET P&L for
  limit checks are **unavailable** (fail safe; do not invent).

**Session NET P&L** (hard-limit metric):

```text
session_net_pnl = equity - start_equity
```

when equity is computable; else undefined for threshold evaluation.

**Unrealized** (when LONG and safe mark):

```text
unrealized_gross = (P_mark - entry_ref_price) * qty
# Session NET already includes MTM via equity; unrealized is displayed
# distinctly for UI. Fees/slippage already paid on entry remain in cash.
```

**Displayed session economics** (distinct fields):

| Field | Meaning |
|-------|---------|
| `grossPnl` | Sum of realized gross + current unrealized gross (when mark safe) |
| `fees` | Cumulative fees paid on all fills |
| `slippageCost` | Cumulative slippage costs on all fills |
| `netPnl` | `session_net_pnl` when computable (= equity − start_equity) |
| `tradeCount` | Count of simulated fills (including forced closes) |

Invariant to test: after any fill while FLAT, `cash == start_equity + netPnl`.
While LONG with safe mark, `equity == cash + qty * P_mark` and
`netPnl == equity - start_equity`.

---

## Decision 4: Profit target / max loss vs unrealized

**Decision**: Evaluate `target_net_profit` and `max_session_loss` using
**Session NET P&L only when equity is computable** (FLAT, or LONG with safe
mark). Unrealized P&L **is included** via mark-to-market inside equity.

| Threshold | Fire when |
|-----------|-----------|
| Profit target | `session_net_pnl >= target_net_profit` |
| Max loss | `session_net_pnl <= -max_session_loss` |
  (`max_session_loss` stored as a **positive** magnitude) |

**Evaluation points** (at least): after every simulated fill; after every
closed-candle pipeline pass when a safe mark exists; on explicit status
refresh used by the worker before continuing.

**When LONG and mark unsafe**: do **not** treat profit/loss thresholds as
hit or cleared by invention. Reject new signal execution (`invalid_or_stale_market_data`).
Duration, max trades, manual stop, and emergency stop still apply. Persistent
inability to obtain safe data MAY escalate to hard stop
`unrecoverable_unsafe_market_data` (worker policy: e.g. consecutive failed
safe-quote attempts ≥ N, document N=3 in implementation/tasks).

**Rationale**: Matches FR-014; prevents fake stop/continue under uncertainty.

**Alternatives considered**:
- Realized-only limits: understates risk while long; rejected by spec.
- Assume last mark forever when stale: violates fail-safe.

---

## Decision 5: Session state transitions

**Decision**: Explicit states:

```text
CONFIGURED → RUNNING → STOPPING → STOPPED
```

| State | Meaning |
|-------|---------|
| `CONFIGURED` | Bounds stored; not executing; may be started if no other active session |
| `RUNNING` | Worker may evaluate closed candles and execute approved sims |
| `STOPPING` | Stop reason recorded; attempting optional forced flatten; no new strategy-driven entries |
| `STOPPED` | Terminal for execution; inspectable journals/economics remain |

**Transitions**:

| From | To | Trigger |
|------|----|---------|
| — | `CONFIGURED` | Create session with valid bounds |
| `CONFIGURED` | `RUNNING` | Start (only if no other RUNNING/STOPPING session) |
| `RUNNING` | `STOPPING` | Manual stop, emergency stop, profit/loss/trades/duration hit, unrecoverable unsafe data, or shutdown recovery handoff |
| `STOPPING` | `STOPPED` | Flatten attempt finished (closed or unsafe-unflattened) and stop finalized |

**Stop reasons** (non-exhaustive enum): `manual`, `emergency`, `profit_target`,
`max_loss`, `max_trades`, `duration_elapsed`, `unrecoverable_unsafe_market_data`,
`backend_restart`.

**Flags**: `position_flatten_status`: `flat` | `forced_closed` | `unsafe_unflattened`.

Emergency stop and automatic hard limits both enter `STOPPING` then `STOPPED`;
emergency sets reason `emergency` and still attempts forced close if safe price
exists.

**Rationale**: Makes “no new execution after stop” testable and supports
flatten-without-inventing-price.

**Alternatives considered**:
- Single ACTIVE/INACTIVE: too coarse for flatten-in-progress.
- PAUSED: not required for Feature 003.

---

## Decision 6: SQLite for durable domain state

**Decision**: Introduce **SQLite** via **SQLAlchemy 2.x** with
`sqlite:///` URL. Default path `backend/data/simulation.db` (override
`SIMULATION_DB_PATH`). Create schema with `metadata.create_all` on startup for
v1 (no Alembic yet). Persist: sessions, decision journal rows, trade journal
rows, and session progress (`last_processed_candle_open_time`).

**Rationale**: Constitution XV; sessions/journals are domain records (unlike
Feature 002 `localStorage` UI prefs). SQLAlchemy keeps models aligned with
`data-model.md` without heavy migration machinery for a local single-operator
app.

**Alternatives considered**:
- JSON files: weaker querying/integrity for journals.
- PostgreSQL now: unnecessary for local-only Feature 003.
- Alembic from day one: valuable later; deferred for intentional simplicity.

---

## Decision 7: Restart / recovery semantics

**Decision**: On backend startup / lifespan:

1. Open DB; create tables if needed.
2. Find any session in `RUNNING` or `STOPPING`.
3. Transition each to `STOPPED` with `stop_reason = backend_restart`.
4. If position was LONG, set `position_flatten_status = unsafe_unflattened`
   (do **not** auto-place a simulated flatten on restart — that would be
   unexpected execution without an explicit operator stop in this boot path).
5. Do **not** start the worker for recovered sessions.
6. Operator must create/start a **new** session to trade again (`CONFIGURED` →
   `RUNNING`). At most one non-terminal active session remains enforceable:
   after recovery, zero RUNNING/STOPPING sessions exist.

**Rationale**: “Cannot silently resume or execute an old simulation session.”

**Alternatives considered**:
- Auto-resume RUNNING: silent unexpected trading — rejected.
- Auto-flatten on boot using live quote: still unexpected execution — rejected
  for Feature 003.

---

## Decision 8: Structural sim vs real-money separation

**Decision**:

- Package all fills under `simulation/execution/`.
- `ExecutionEngine` protocol with `execute(intent) -> FillResult`.
- `SimulationExecutionEngine` is the only wired implementation for sessions.
- `UnavailableRealMoneyExecution` always rejects with
  `real_money_unavailable`.
- Session `mode` is always `simulation` for creatable sessions; API MUST reject
  create/start with `mode=real_money`.
- Strategy, Controller, and Risk MUST depend on normalized market models +
  execution port — never XT adapters or private APIs.
- Future real XT execution would add a new engine behind the same port and a
  separate explicit activation path (out of scope now).

**Rationale**: Prevents accidental bypass when real money arrives later.

**Alternatives considered**:
- Single `ExecutionEngine` with a boolean `simulate=True`: easier to misuse.
- Strategy calling market_data adapter directly: leaks XT risk into control
  plane — forbidden.

---

## Decision 9: Deterministic time handling

**Decision**: Introduce `Clock` protocol:

- `now() -> datetime` (timezone-aware UTC).
- `SystemClock` for production.
- `FakeClock` for tests (`set` / `advance`).

Use `Clock` for:

- Session `started_at` / duration expiry (`now >= started_at + duration`).
- Candle **closed** detection: a bar with `open_time` is closed iff
  `now >= open_time + interval_duration`. The worker requests candles from
  Feature 002 service, considers only bars that are closed under `Clock`, and
  processes the newest closed bar strictly newer than
  `last_processed_candle_open_time`.
- Journal timestamps.

**Duplicate prevention**: Persist `last_processed_candle_open_time` per session.
The same `open_time` MUST NOT enter strategy evaluation twice.

**Forming candle**: If the newest bar is not yet closed per `Clock`, ignore it
for signaling (no intrabar evaluation).

**Rationale**: Testable duration + close semantics without sleeping in unit
tests.

**Alternatives considered**:
- Always trust exchange “last candle is closed”: ambiguous for forming bars.
- Wall-clock only: flaky tests.

---

## Decision 10: Trading-critical automated tests

**Decision**: Require automated coverage at least for:

| Area | Assertions |
|------|------------|
| Accounting invariants | Equity/NET formulas; fee/slippage defaults; round-trip cash |
| Position sizing | `min(affordable, max_position_size)`; reject when cannot afford |
| State transitions | Legal transitions only; no exec in STOPPED |
| Duplicate candle | Second pass same `open_time` → no re-eval / no second fill |
| Rejected signals | BUY while LONG, SELL while FLAT, stale data, max trades, etc. journaled |
| HOLD | Decision journaled; no trade; no balance change |
| Hard stops | Profit/loss (with unrealized), duration, max trades → STOPPING/STOPPED |
| Unsafe market data | No fabricated prices; reject/suspend |
| Forced close | Safe price → SELL + trade journal; unsafe → unsafe_unflattened |
| Recovery | RUNNING on boot → STOPPED `backend_restart`; worker not resumed |
| Pipeline authority | Strategy cannot mutate balances without controller/risk/sim engine |
| API mode | Real-money create/start rejected |

**Rationale**: Constitution XXVIII.

---

## Decision 11: Market-data consumption & “safe” price

**Decision**: Simulation code calls Feature 002 **internal**
`market_data.service` (or equivalent) returning normalized models — not XT
adapter types. Align “safe” with Feature 002 quote freshness: prefer
`observedAt` else `retrievedAt`; age ≤ **60 seconds** and payload valid → safe.
STALE or missing/malformed → unsafe for execution and for MTM hard-limit
equity when LONG.

Candles: use normalized OHLC; strategy uses closed bars only (Decision 9).
Candle age does not redefine quote safety.

**Rationale**: FR-002, FR-021, adapter isolation.

**Alternatives considered**:
- Re-implement XT fetch inside simulation: forbidden.
- Use candle close as mark price only: acceptable fallback only if explicitly
  specified; Feature 003 prefers quote last for marks/fills when safe.

---

## Decision 12: Worker / polling (no WebSockets)

**Decision**: While `RUNNING`, a backend asyncio task polls on a short interval
(e.g. 1–5s): load session, check duration/limits, fetch quote+candles via
market_data service, process at most one new closed candle per wake, persist,
evaluate stops. No WebSockets.

**Rationale**: Spec forbids WebSockets; polling is enough for closed-candle
demo timeframes (15m+).

**Alternatives considered**:
- WebSocket klines: out of scope.
- Evaluate only on user HTTP refresh: would miss unattended session stops.

---

## Decision 13: Decision Journal contents

**Decision**: Every closed-candle evaluation writes a Decision Journal row for
`HOLD`, **approved** non-HOLD, and **rejected** non-HOLD (with reason). Forced
closes are Trade Journal events; also record a decision row with
`signal=SELL`, `outcome=forced` / reason `hard_stop_flatten` when applicable.

**Rationale**: User-locked requirement that Decision Journal records HOLD,
approved, and rejected decisions.
