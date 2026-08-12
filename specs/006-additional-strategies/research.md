# Research: Additional Strategies

**Feature**: `006-additional-strategies`  
**Date**: 2026-08-12

All Technical Context items resolved; no remaining NEEDS CLARIFICATION.
Clarifications from Session 2026-08-12 are treated as locked decisions.

---

## Decision 1: Four modules + auto-register via package import

**Decision**: Add `rsi.py`, `macd.py`, `bollinger.py`, `breakout.py` under
`backend/app/strategy/`, each calling `register(...)` at module load (same
pattern as `dual_ema.py`). Update `app.strategy.__init__` (and `main.py` if
needed) to import all five so registration is complete on app start.

**Rationale**: Matches Feature 005; FR-012 forbids strategy-specific branches
in simulation/backtest engines — registration is sufficient for
`validate_and_materialize` / `build_from_stored`.

**Alternatives considered**:
- Central `register_all()` with explicit list — slightly clearer, but diverges
  from Dual EMA’s proven import-side registration.
- Plugin discovery via entry points — overkill (constitution X).

---

## Decision 2: Shared `indicators.py` for EMA/SMA; Dual EMA may adopt later

**Decision**: Introduce `app.strategy.indicators` with Decimal-based helpers:
EMA (SMA seed then k=2/(n+1) smoothing — same as Dual EMA today), SMA,
population stdev, Wilder RSI series. New strategies use these helpers. Dual
EMA may keep its local `_ema` **unchanged** in this feature to avoid
continuity risk, or optionally call the shared helper only if golden tests
still match bit-for-bit.

**Rationale**: MACD needs the same EMA semantics as Dual EMA; sharing prevents
silent forks. Leaving Dual EMA code untouched by default satisfies FR-013 /
SC-005.

**Alternatives considered**:
- Copy `_ema` into MACD — simpler diff, higher drift risk.
- Force Dual EMA refactor in the same PR — unnecessary continuity risk.

---

## Decision 3: RSI — Wilder smoothing + recovery crossover

**Decision**: Compute RSI with Wilder’s method (average gain/loss smoothed
with α = 1/period after seed SMA of first `period` changes). Signal rule
(locked): BUY when RSI crosses from &lt; oversold to ≥ oversold; SELL when
crosses from &gt; overbought to ≤ overbought; else HOLD. `S = period`.

**Rationale**: Spec assumptions + clarify Q1. Recovery (not “enter zone”)
avoids spam while RSI stays extreme.

**Alternatives considered**:
- Level signals while beyond thresholds — rejected in clarify.
- SMA-only RSI (no Wilder) — less conventional for “RSI”.

---

## Decision 4: MACD — line/signal crossover; `S = slow + signal`

**Decision**: MACD line = EMA(fast) − EMA(slow); signal = EMA(MACD line,
signalPeriod) using the same EMA seeding style as Dual EMA on the MACD-line
series once both EMAs are available. BUY when MACD crosses from ≤ signal to
&gt; signal; SELL when from ≥ to &lt;. `S = slowPeriod + signalPeriod` as the
Feature 006 conventional accept gate (not a claim of perfect seed maturity).
HOLD until `S+1` for prior-bar comparison.

**Rationale**: Clarify Q3 explicitly accepted this formula as the cleanest
framework rule aligned with Dual EMA’s `S` / `S+1` contract.

**Alternatives considered**:
- Stricter `S` requiring full triple-EMA maturity — deferred; may refine later
  without changing the accept/`S+1` contract shape.
- Histogram zero-cross — out of scope; keep line/signal only.

---

## Decision 5: Bollinger — SMA + population σ; recovery crossover

**Decision**: Middle = SMA(period); σ = population stdev of the same window
(divide by `period`, not `period-1`); bands = middle ± stdDev × σ. BUY when
close crosses from &lt; lower to ≥ lower; SELL when from &gt; upper to ≤ upper;
else HOLD. `S = period`. Persist `stdDev` as `decimal_string` (e.g. `"2.0"`).

**Rationale**: Spec assumptions + clarify Q2. `ParamDef` already supports
`decimal_string`.

**Alternatives considered**:
- Sample stdev (n−1) — common in some libraries; spec chose population.
- Level signals while outside bands — rejected in clarify.

---

## Decision 6: Breakout — every new extreme on prior closes

**Decision**: For lookback `L`, compare current close to
`max(closes[-L-1:-1])` and `min(closes[-L-1:-1])` (current bar excluded).
BUY if close &gt; prior high; SELL if close &lt; prior low; else HOLD.
Repeat on successive new extremes. `S = lookback`.

**Rationale**: Clarify Q4 — trend-following continuation, not first-break-only
and not mean-reversion recovery.

**Alternatives considered**:
- First-break-only / recovery style — rejected.
- Use high/low OHLC — out of scope; closes only (CandleClose contract).

---

## Decision 7: No API/schema migration; extend list contract only

**Decision**: Do not add columns or new endpoints. Extend `GET /strategies`
documented response to five entries. Update frontend `FALLBACK_STRATEGIES` to
mirror all five schemas so offline/loading UX stays usable. Simulation/
backtest create bodies already accept any registered `strategyId` +
`strategyParams`.

**Rationale**: FR-011–FR-012; Feature 005 already built the pluggable path.

**Alternatives considered**:
- Per-strategy REST resources — unnecessary.
- Hard-code UI fields per strategy — forbidden by FR-014.

---

## Decision 8: Golden fixtures per strategy; Dual EMA tests untouched

**Decision**: Each new strategy gets a locked closed-price fixture and
expected BUY/SELL/HOLD sequence under defaults. Dual EMA continuity tests
must pass without modification (SC-005). At least one integration assertion
that sim and backtest resolve the same class for a non–Dual-EMA id.

**Rationale**: SC-003 / SC-005; constitution XXVII–XXIX.

**Alternatives considered**:
- Spot-check only without golden sequences — weaker regression safety.
