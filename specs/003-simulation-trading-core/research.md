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
4. Maximum affordable notional from **current cash** (cash must cover notional
   + fee):

   `affordable_notional = current_cash / (1 + fee_rate)`

5. Intended full notional (**enforceable** triple bound):

   ```text
   intended_notional = min(
       affordable_notional,
       allocated_capital,
       max_position_size
   )
   ```

   `allocated_capital` is an enforceable trading bound: the simulation MUST NOT
   deploy more than `allocated_capital` notional even when `starting_capital`
   or `current_cash` is larger. `max_position_size` remains an additional USDT
   notional cap.

6. If `intended_notional <= 0` (or below a documented dust floor, e.g. notional
   that would round to zero quantity), **reject** (`insufficient_balance` and/or
   `allocated_capital_exceeded` / `position_size_limit` as applicable) — do
   **not** silently shrink to a partial “almost full” size below the intended
   rule after approval.

7. Base quantity: `qty = intended_notional / P_fill` (decimal arithmetic).

8. Fill notional `N = qty * P_fill`; fee `F = N * fee_rate`; cash debit
   `N + F`; position becomes LONG with `qty` and cost basis recorded as
   `N + F` (cash outlay).

**SELL (full close)**:

1. `P_fill = P_ref * (1 - slippage_rate)` (adverse for sell).
2. `N = qty * P_fill`; `F = N * fee_rate`; cash credit `N - F`; position → FLAT.
3. Quantity closed is always the **entire** open `qty`.

**Starting vs allocated capital**: Session starts flat with
`cash = starting_capital`. `allocated_capital` MUST be configured explicitly
(positive) and enforced in sizing as above. v1 UI MAY default
`allocated_capital` to equal `starting_capital` when the operator enters a
single capital figure, but both fields remain distinct in session semantics
and storage. If `starting_capital > allocated_capital`, excess cash is held
but MUST NOT be deployed beyond `allocated_capital` on a full BUY.

**Rationale**: Matches long-only full-position model; makes allocated capital a
real risk bound, not documentary-only; keeps fee coverage explicit; rejects
rather than silent partials.

**Alternatives considered**:
- Cap only by cash and max_position_size (ignore allocated): rejected — user
  requires allocated_capital enforceable.
- Always deploy 100% of starting capital ignoring caps: violates session bounds.
- Partial fills to use leftover cash dust: conflicts with single full-position
  simplicity.
- Allow notional above allocated when cash is larger: rejected.

---

## Decision 2a: Profit target and max loss as % of allocated capital

**Decision**: The operator configures **rates** (percentages of
`allocated_capital`), not ambiguous raw currency amounts as the primary input.

Example:

| Input | Value |
|-------|--------|
| `allocated_capital` | `500` USDT |
| `target_net_profit_rate` | `0.01` (1.0%) |
| `max_session_loss_rate` | `0.007` (0.7%) |

Derived absolute thresholds (computed at session create/start and stored):

```text
target_net_profit_amount = allocated_capital * target_net_profit_rate
max_session_loss_amount  = allocated_capital * max_session_loss_rate
```

Example → target amount `5.00` USDT; max loss amount `3.50` USDT.

**Persistence / audit**: Store **both** the configured rates and the derived
absolute amounts on the session so journals, economics, and stop reasons remain
auditable if display conventions change.

**Hard-limit comparison** (unchanged metric): liquidation-based Session NET P&L
is compared to these **derived absolute** thresholds:

| Threshold | Fire when |
|-----------|-----------|
| Profit target | `session_net_pnl_for_limits >= target_net_profit_amount` |
| Max loss | `session_net_pnl_for_limits <= -max_session_loss_amount` |

**UI**: Auto Trading MUST show both the configured **percentage** and the
resulting **currency amount** for target and max loss (e.g. “1.0% → 5.00 USDT”
given allocated 500).

Rates are fractions in storage/API (`"0.01"` = 1%); UI MAY accept percent-point
entry (`1.0`) and convert.

**Rationale**: Removes ambiguity between currency vs percent; keeps liquidation
NET as the evaluation metric; dual storage aids audit.

**Alternatives considered**:
- Raw USDT-only config: ambiguous and error-prone — rejected for Feature 003.
- Percent of starting_capital: rejected — user requires percent of allocated.
- Store rates only and re-derive later without persisting amounts: weaker
  audit trail — rejected.

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

### Session aggregates — mark equity vs liquidation equity

- `start_equity = starting_capital` (session starts flat).
- `cash` = running simulated cash.

**Informational mark-to-market** (display only; not the hard-limit metric while LONG):

- If FLAT: `mark_equity = cash`.
- If LONG and **safe** mark `P_mark` available:  
  `mark_equity = cash + qty * P_mark`  
  (`P_mark` is safe last **without** slippage — valuation only).
- `unrealized_gross = (P_mark - entry_ref_price) * qty` when LONG and mark safe.
- If LONG and **no** safe mark: mark equity / unrealized are unavailable (do not invent).

**Liquidation equity** (hard-limit Session NET P&L basis while LONG):

When FLAT:

```text
liquidation_equity = cash
```

When LONG and **safe** mark `P_mark` (`P_ref`) available, compute a **hypothetical**
full adverse SELL with the same rules as Decision 2 (do not mutate cash yet):

```text
P_fill_hyp = P_mark * (1 - slippage_rate)
N_hyp = qty * P_fill_hyp
F_hyp = N_hyp * fee_rate
net_sell_proceeds_hyp = N_hyp - F_hyp
liquidation_equity = cash + net_sell_proceeds_hyp
```

When LONG and mark unsafe: liquidation equity / hard-limit Session NET P&L are
**unavailable** (fail safe; do not invent).

**Session NET P&L for profit-target / max-loss evaluation**:

```text
session_net_pnl_for_limits = liquidation_equity - start_equity
```

when liquidation equity is computable; else undefined for those thresholds.

Rationale: a profit target means profit that could actually be **secured** under
the session’s fee and slippage assumptions, not raw mark value.

### No double-counting of exit costs

Hypothetical liquidation math is used **only** to decide whether a profit/loss
hard stop fires. It MUST NOT debit cash, increment fees/slippage ledgers, or
write a Trade Journal row by itself.

When a hard stop then performs a **real** forced SELL:

1. Execute one actual full close with the same fee/slippage formulas.
2. Apply fee and slippage **once** via that fill to cash and cumulative ledgers.
3. Journal the fill with `is_forced_close=true`.
4. Do **not** also subtract the previously computed hypothetical `F_hyp` /
   slippage again.

After the forced close, the session is FLAT and
`cash - start_equity` equals the realized Session NET (actual costs applied
once). While still LONG, display may show both mark-based and liquidation-based
figures; only liquidation-based NET drives target/max-loss.

**Displayed session economics** (distinct fields):

| Field | Meaning |
|-------|---------|
| `markEquity` | Informational MTM equity (`cash + qty * P_mark` when long+safe) |
| `markNetPnl` | `markEquity - startEquity` (informational) |
| `unrealizedGross` | Informational unrealized gross when mark safe |
| `liquidationEquity` | Hard-limit equity basis (`cash` when flat; hyp. net SELL when long+safe) |
| `netPnl` | **Hard-limit** Session NET = `liquidationEquity - startEquity` when computable |
| `grossPnl` | Realized gross + current unrealized gross (informational) |
| `fees` | Cumulative fees paid on **actual** fills only |
| `slippageCost` | Cumulative slippage on **actual** fills only |
| `tradeCount` | All simulated fills including forced closes |
| `strategyFillCount` | Strategy-driven fills only (see Decision 4a) |

Invariant to test: after any fill while FLAT, `cash == start_equity + netPnl`
(and mark/liquidation equity both equal cash). While LONG with safe mark,
`netPnl` for limits uses liquidation equity, not raw mark equity; after a forced
close matching the same `P_mark`/rates, post-close `cash` equals the pre-close
hypothetical `liquidation_equity` (within decimal rounding rules).

---

## Decision 4: Profit target / max loss vs liquidation NET

**Decision**: Evaluate thresholds using **liquidation-based Session NET P&L**
only when liquidation equity is computable (FLAT, or LONG with safe mark).
Operator-configured inputs are **rates of allocated_capital** (Decision 2a);
comparison uses the stored **derived absolute amounts**.

| Threshold | Fire when |
|-----------|-----------|
| Profit target | `session_net_pnl_for_limits >= target_net_profit_amount` |
| Max loss | `session_net_pnl_for_limits <= -max_session_loss_amount` |
  (`max_session_loss_amount` is a **positive** magnitude) |

Raw mark-to-market equity and unrealized gross MAY be shown in UI/economics but
MUST NOT be the profit-target / max-loss trigger while LONG.

**Evaluation points** (at least): after every simulated fill; after every
closed-candle pipeline pass when a safe mark exists; on explicit status
refresh used by the worker before continuing.

**When LONG and mark unsafe**: do **not** treat profit/loss thresholds as
hit or cleared by invention. Reject new signal execution (`invalid_or_stale_market_data`).
Duration, max trades, manual stop, and emergency stop still apply. Persistent
inability to obtain safe data MAY escalate to hard stop
`unrecoverable_unsafe_market_data` (worker policy: e.g. consecutive failed
safe-quote attempts ≥ N, document N=3 in implementation/tasks).

**Rationale**: Securable NET under documented costs; absolute thresholds derived
transparently from allocated capital percentages.

**Alternatives considered**:
- Raw MTM equity for limits: can stop “in profit” that fees/slippage would erase
  on exit — rejected.
- Compare rates directly to NET/allocated without storing amounts: weaker audit
  — rejected (store both).
- Realized-only limits: understates open risk — rejected.
- Assume last mark forever when stale: violates fail-safe.

---

## Decision 4a: `max_trades` semantics

**Decision**:

- `max_trades` limits **normal strategy-driven** simulated fills only (approved
  BUY/SELL that originate from the strategy → controller → risk → execution
  path, including ordinary strategy SELLs).
- Maintain `strategy_fill_count` for that gate and `trade_count` for all fills
  (strategy + forced).
- When `strategy_fill_count` reaches `max_trades`, the session MUST enter the
  stop path (`stop_reason = max_trades`): no further strategy-driven execution.
- If that stop occurs while **LONG**, **one** forced safety close is still
  allowed even if it makes `trade_count == max_trades + 1`. That fill MUST be
  journaled with `is_forced_close=true` and MUST NOT enable any additional
  strategy execution afterward.
- If already FLAT when `max_trades` is reached, no forced close is needed.
- Forced closes from other stop reasons (profit/loss, duration, emergency,
  manual, unsafe-data escalate) follow the same “one safety close, journaled,
  no further strategy exec” rule; they are not strategy-driven and do not
  consume the `max_trades` budget, but they do increment `trade_count`.

**Rationale**: Hard stop must be able to flatten without being blocked by the
trade cap that triggered or coincided with termination.

**Alternatives considered**:
- Count forced closes against `max_trades` and block flatten: unsafe — rejected.
- Unlimited forced closes: unnecessary; at most one flatten is required.

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

- Keep an `ExecutionEngine` protocol (`execute(intent) -> FillResult`) so
  simulation fills stay behind a clear port.
- Feature 003 ships **only** `SimulationExecutionEngine` — do **not** add a
  real-money / XT execution implementation (stub or otherwise) in this feature.
- Reject `mode=real_money` explicitly at the **API / session** boundary
  (`real_money_unavailable`). Creatable sessions are always `simulation`.
- Strategy, Controller, and Risk MUST depend on normalized market models + the
  simulation execution path — never XT adapters or private APIs.
- Future real XT execution remains **entirely out of scope** for Feature 003;
  a later feature may add a separate engine behind the same port with an
  explicit activation path.

**Rationale**: Preserve the abstraction without shipping unused real-money code
paths that invite accidental wiring.

**Alternatives considered**:
- `UnavailableRealMoneyExecution` class in-tree: unnecessary surface for 003 —
  rejected in favor of API rejection only.
- Boolean `simulate=True` on a shared engine: easier to misuse.
- Strategy calling market_data adapter directly: forbidden.

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
| Accounting invariants | Mark vs liquidation equity; limit NET uses liquidation; fee/slippage defaults; round-trip cash |
| No double-count | Hyp. liquidation costs not ledgered; actual forced close applies costs once |
| Position sizing | `min(affordable, allocated_capital, max_position_size)`; never above allocated |
| Profit/loss config | Rates of allocated → stored amounts; limits compare liquidation NET to amounts |
| State transitions | Legal transitions only; no exec in STOPPED |
| Duplicate candle | Second pass same `open_time` → no re-eval / no second fill |
| Rejected signals | BUY while LONG, SELL while FLAT, stale data, max trades, etc. journaled |
| HOLD | Decision journaled; no trade; no balance change |
| Hard stops | Profit/loss via liquidation NET, duration, max trades → STOPPING/STOPPED |
| max_trades | Strategy fills capped; one forced close may make `trade_count = max_trades + 1` |
| Unsafe market data | No fabricated prices; reject/suspend |
| Forced close | Safe price → SELL + `is_forced_close`; unsafe → unsafe_unflattened |
| Recovery | RUNNING on boot → STOPPED `backend_restart`; worker not resumed |
| Pipeline authority | Strategy cannot mutate balances without controller/risk/sim engine |
| API mode | Real-money create/start rejected; no real-money engine module required |

**Rationale**: Constitution XXVIII.

---

## Decision 11: Market-data consumption & “safe” price

**Decision**: Simulation code calls Feature 002 **internal**
`market_data.service` (or equivalent) returning normalized models — not XT
adapter types. Align “safe” with Feature 002 quote freshness: prefer
`observedAt` else `retrievedAt`; age ≤ **60 seconds** and payload valid → safe.
STALE or missing/malformed → unsafe for execution and for liquidation-equity
hard-limit evaluation when LONG.

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
