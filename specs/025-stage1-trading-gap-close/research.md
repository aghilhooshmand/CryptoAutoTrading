# Research: Feature 025 — Stage-1 Trading Gap-Close

**Date**: 2026-08-16  
**Branch**: `025-stage1-trading-gap-close`  
**Sources**: Clarified `spec.md` (Session 2026-08-16 Q1–Q6); repository
(`pipeline.py`, `backtest/engine.py`, `strategy/base.py`, `market_data` models);
constitution I–V, VIII, X–XII, XXXII.

---

## R1 — Protective TP/SL as trigger → SELL intent (not a fill price)

**Decision**: Implement TP/SL as **closed-candle trigger detection** that emits a
protective **SELL** intent through Controller → Risk → Execution. Fill price
follows each mode’s existing model:

| Mode | Trigger | Fill |
|------|---------|------|
| Simulation | candle `high`/`low` vs absolute levels | trustworthy **live mark** (existing) |
| Backtest | candle `high`/`low` vs absolute levels | **next candle open** (existing) |

Never fill at the TP/SL trigger level.

**Rationale**: Clarifications Q1 + Q4; never invent; preserve Feature 003/004
economics.

**Alternatives considered**:
- Fill at TP/SL level — rejected (invented limit fill).
- Close-only triggers — rejected (Q1 chose high/low).
- Unify Sim and Backtest fill models — rejected (intentional difference).

---

## R2 — Evaluation order and entry-bar skip

**Decision**: On each newly processed closed candle while long:

1. Existing session/emergency hard-stops (unchanged; first).
2. If candle is the **entry-fill candle** → skip TP/SL.
3. Else if `low ≤ stop_loss_price` → protective SL exit (wins if TP also touched).
4. Else if `high ≥ take_profit_price` → protective TP exit.
5. Else strategy evaluate → Controller → Risk → Execution as today.

Store `entry_fill_candle_open_time` (or equivalent) when BUY fills so the skip
is deterministic.

**Rationale**: Spec precedence + Q5.

**Alternatives considered**: Evaluate on entry bar — rejected (Q5).

---

## R3 — Percentage config and derived absolute levels

**Decision**:

- Operator fields: optional `takeProfitPercent` / `stopLossPercent` as positive
  decimal **fractions** of entry (same string/decimal style as session loss
  rates), independently omittable.
- On BUY fill:  
  `take_profit_price = entry_fill * (1 + tp%)`  
  `stop_loss_price = entry_fill * (1 - sl%)`  
  (long-only). Reject at create/start if percent ≤ 0 or would imply non-positive
  SL / inverted levels.
- Persist percentages on session/backtest config; persist absolute prices on
  position state; clear absolutes on flat.
- No mid-position edits (Q6).

**Rationale**: Q3 + Q6; mirrors existing rate→amount patterns.

**Alternatives considered**: Editable absolute prices — rejected (Q3).

---

## R4 — Shared semantics, separate engines

**Decision**: Keep Simulation `pipeline.py` and Backtest `engine.py` as separate
loops but share:

- percent validation / absolute derivation helpers;
- trigger predicate (high/low, entry-bar skip, SL-before-TP);
- exit reason codes (`take_profit`, `stop_loss`, plus existing strategy/session
  codes).

Do not merge engines.

**Rationale**: Spec intentional fill divergence; avoid large refactor in a
gap-close feature.

**Alternatives considered**: Single unified engine — rejected (scope/risk).

---

## R5 — OHLC strategy candle enrichment

**Decision**: Extend `CandleClose` (name may remain for compatibility or rename
to a candle bar type in implement) to include **open, high, low, close** (+
optional volume fields unused by required strategies). Existing five strategies
continue to read **close only** (behavior unchanged). Simulation lookback and
Backtest series already have OHLC on `Candlestick` — stop dropping high/low when
building strategy inputs.

**Rationale**: Q2; Stochastic/Keltner need range.

**Alternatives considered**: Close-only new strategies — rejected (Q2).

---

## R6 — Additional strategies and volume gate

**Decision**: Register **three** required new strategies:

| ID (proposed) | Concept |
|---------------|---------|
| `stochastic` | %K/%D style oscillator on high/low/close |
| `keltner_channel` | ATR-based channel; recovery/break signals analogous in simplicity to Bollinger |
| `roc_momentum` | Rate-of-change / momentum on close |

**Relative volume**: **DEFER**. XT `volumeBase`/`volumeQuote` are optional in
mapping; not consumed by engines today; reliability not proven for all
symbols/intervals. Do not block Feature 025.

Exact default parameters finalized in tasks/implement within registry ParamDef
norms (keep small).

**Rationale**: Spec diversity + FR-014; repository volume evidence.

**Alternatives considered**: Force volume strategy — rejected (unreliable gate).

---

## R7 — Intentional Sim vs Backtest documentation

**Decision**: Publish a short contract note
([contracts/sim-vs-backtest-semantics.md](./contracts/sim-vs-backtest-semantics.md))
listing intentional differences (mark vs next-open; protective exits inherit
same) and stating that TP/SL **rules** (%, levels, high/low, precedence,
accounting after fill) must match. Fix only accidental divergences found in
tests.

**Rationale**: Spec FR-012 / US3.

---

## R8 — UI / API surface

**Decision**: Minimal fields only:

- Create Simulation / Backtest / optional Settings defaults: TP%/SL% optional.
- Active session: `entryFillPrice`, `takeProfitPrice`, `stopLossPrice` when long;
  exit/stop reason already partially present — ensure TP/SL reasons visible.
- No Portfolio redesign; no mid-position editors.

**Rationale**: FR-016; Q6.

---

## R9 — Persistence / SQLite

**Decision**: Add nullable columns via models + `init_db` `_ensure_column` (same
pattern as Feature 014). No separate migration framework.

**Rationale**: Existing project pattern.

---

## Open items deferred to tasks (not product ambiguities)

- Exact Stochastic / Keltner / ROC default parameters and signal rules (keep
  deterministic and simple; finalize in implement within registry ParamDef norms).
- README one-liner pointer to sim-vs-backtest contract.

### Locked during analyze remediation (2026-08-16)

**Protective exits vs `maxTrades`**: Protective TP/SL closes MUST use the
forced/safety path (Simulation `is_forced=True` / Backtest equivalent). They do
**not** increment `strategyFillCount` and do **not** consume `maxTrades` slots
(Feature 003 strategy-driven fill limit). Reasons remain `take_profit` /
`stop_loss`. See `contracts/protective-exits.md`.
