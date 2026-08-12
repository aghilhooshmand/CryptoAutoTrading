# Feature Specification: Additional Strategies

**Feature Branch**: `006-additional-strategies`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Feature 006 — Additional Strategies: add RSI, MACD, Bollinger Bands, and Breakout to the existing strategy framework. Each implements the shared strategy contract, registers via the registry, exposes parameters with defaults and validation, returns BUY/SELL/HOLD only, and works identically in Simulation and Backtest. Keep strategies simple and deterministic. No optimization, ranking, ML, multi-strategy, sentiment, leverage, shorting, or real-money trading."

## Clarifications

### Session 2026-08-12

- Q: Should RSI emit BUY/SELL only on threshold crosses, or while remaining beyond the threshold? → A: Crossover on recovery only — BUY when RSI crosses upward out of oversold; SELL when RSI crosses downward out of overbought; HOLD otherwise.
- Q: When should Bollinger Bands emit BUY or SELL relative to the bands? → A: Recovery crossover (Option A) — BUY when close crosses from below the lower band to at/above it; SELL when close crosses from above the upper band to at/below it; HOLD otherwise.
- Q: How should each strategy’s minimum closed-candle history (`S` / `min_history_candles`) relate to Dual EMA’s reject-at-`S` / HOLD-until-`S+1` rule? → A: Option A with explicit `S`: RSI=`period`; MACD=`slowPeriod + signalPeriod` (conventional lower bound for this feature); Bollinger=`period`; Breakout=`lookback`. Backtest with fewer than `S` candles → `insufficient_history`; at exactly `S` → accepted but strategy returns HOLD; from `S+1` onward → crossover may be evaluated using current + previous indicator state.
- Q: Should Breakout emit on every new extreme or only the first break of the range? → A: Every new extreme (Option A) — BUY whenever close exceeds the prior lookback high; SELL whenever close falls below the prior lookback low; HOLD otherwise. Breakout is trend-following; repeated new highs/lows are continuing-trend evidence, not treated as signal spam (unlike RSI/Bollinger mean-reversion recovery events).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select RSI for simulation and backtest (Priority: P1)

An operator configuring a simulation or backtest under Auto Trading sees RSI in the strategy selector alongside Dual EMA, can accept defaults (period 14, overbought 70, oversold 30) or edit valid parameters, and run a session or backtest that evaluates RSI signals through the existing Controller → Risk → Execution pipeline.

**Why this priority**: RSI is the most widely recognized momentum oscillator; adding it first validates that the framework supports a second strategy type end-to-end without breaking Dual EMA.

**Independent Test**: Create a simulation session with `strategyId: rsi` and default parameters; confirm session persists `rsi` + effective params; run a backtest with custom thresholds (overbought 75, oversold 25); confirm signals match recovery-crossover semantics (BUY when RSI crosses upward out of oversold; SELL when RSI crosses downward out of overbought; HOLD otherwise).

**Acceptance Scenarios**:

1. **Given** Auto Trading strategy selector, **When** the operator opens session/backtest configuration, **Then** RSI appears as a selectable strategy with default parameters displayed.
2. **Given** RSI selected with valid parameters, **When** the session/backtest runs on closed candles, **Then** the strategy emits BUY when RSI crosses from below oversold to at/above oversold, SELL when RSI crosses from above overbought to at/below overbought, and HOLD otherwise (including while RSI remains beyond a threshold without recovering).
3. **Given** RSI selected with invalid parameters (e.g. oversold ≥ overbought), **When** the operator submits, **Then** the system rejects with a clear constraint message.
4. **Given** the same closed-candle fixture, **When** RSI runs in simulation and backtest, **Then** the signal sequence is identical (shared implementation).

---

### User Story 2 - Select MACD for simulation and backtest (Priority: P1)

An operator selects MACD, accepts defaults (fast 12, slow 26, signal 9) or edits parameters, and runs. MACD emits BUY on bullish crossover (MACD line crosses above signal line), SELL on bearish crossover, and HOLD otherwise.

**Why this priority**: MACD is a trend-following momentum indicator complementary to RSI; registering it proves the framework supports indicator-based crossover strategies beyond EMA.

**Independent Test**: Create a backtest with `strategyId: macd` and defaults; confirm BUY/SELL/HOLD semantics on a crafted price series with known crossovers.

**Acceptance Scenarios**:

1. **Given** MACD selected with defaults (12/26/9), **When** the session runs, **Then** BUY fires on MACD line crossing above signal line; SELL on crossing below; HOLD otherwise.
2. **Given** MACD selected with invalid parameters (e.g. fast ≥ slow), **When** the operator submits, **Then** the system rejects with a clear constraint message.
3. **Given** a fixed candle fixture, **When** MACD runs in simulation and backtest, **Then** signals are identical.

---

### User Story 3 - Select Bollinger Bands for simulation and backtest (Priority: P2)

An operator selects Bollinger Bands, accepts defaults (period 20, standard deviations 2.0) or edits, and runs. The strategy emits BUY when close crosses upward back through the lower band (recovery from below), SELL when close crosses downward back through the upper band (recovery from above), and HOLD otherwise.

**Why this priority**: Bollinger Bands offer a volatility-based mean-reversion approach, widening the strategy type diversity beyond pure trend-following.

**Independent Test**: Create a simulation with `strategyId: bollinger_bands` and defaults; verify BUY/SELL fire only on recovery crossovers through the bands, not on every bar while outside.

**Acceptance Scenarios**:

1. **Given** Bollinger Bands with defaults (20, 2.0), **When** close crosses from below the lower band to at/above it, **Then** signal is BUY.
2. **Given** close crosses from above the upper band to at/below it, **Then** signal is SELL.
3. **Given** close remains inside the bands, or remains outside without crossing back through a band, **Then** signal is HOLD.
4. **Given** invalid parameters (e.g. period < 2, stdDev ≤ 0), **When** operator submits, **Then** rejected with a clear message.

---

### User Story 4 - Select Breakout for simulation and backtest (Priority: P2)

An operator selects Breakout, accepts defaults (lookback 20) or edits, and runs. The strategy emits BUY whenever the current close exceeds the highest close of the prior lookback window, SELL whenever it falls below the lowest close, and HOLD otherwise — including on successive bars that keep printing new extremes (trend continuation).

**Why this priority**: Breakout rounds out the set as a trend-following channel strategy, complementing RSI/Bollinger mean-reversion.

**Independent Test**: Create a backtest with `strategyId: breakout` and a lookback of 10; confirm BUY on each new high beyond the prior window and SELL on each new low, not only the first break.

**Acceptance Scenarios**:

1. **Given** Breakout with lookback 20, **When** current close exceeds the prior 20-bar high, **Then** signal is BUY (including on consecutive new highs).
2. **Given** current close falls below the prior 20-bar low, **Then** signal is SELL (including on consecutive new lows).
3. **Given** close is within the prior range (not a new extreme), **Then** signal is HOLD.
4. **Given** lookback < 2, **When** operator submits, **Then** rejected.

---

### Edge Cases

- Selecting any new strategy with insufficient history for that strategy's minimum requirement `S` → backtest fails with `insufficient_history`; a window with exactly `S` closed candles is accepted but the strategy emits HOLD; crossover evaluation begins only from `S+1`.
- Dual EMA behavior unchanged after new strategies are registered (existing tests and continuity fixture still pass).
- Unknown `strategy_id` still rejected on create and START/RESUME (existing fail-safe unaffected).
- Omitting `strategyId` still rejected (existing FR-006/FR-007 from Feature 005).
- All four new strategies return HOLD when candle count is below `S+1` (no fabricated signals from partial data).
- `GET /strategies` returns all five strategies (Dual EMA + four new) with parameter schemas.
- Strategy parameters persisted and visible on session/backtest inspect surfaces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register RSI as a strategy with canonical `strategy_id` = `rsi`, display name "RSI", parameters: `period` (integer, default 14, min 2), `overbought` (integer, default 70, min 1, max 99), `oversold` (integer, default 30, min 1, max 99). Cross-field constraint: `oversold` MUST be less than `overbought` — message: "Oversold threshold must be less than overbought threshold."
- **FR-002**: RSI MUST emit BUY when the computed RSI value crosses upward out of oversold (from below `oversold` to at/above `oversold`), SELL when it crosses downward out of overbought (from above `overbought` to at/below `overbought`), and HOLD otherwise — including while RSI remains beyond a threshold without recovering across it. RSI MUST emit HOLD during warm-up (insufficient history for the configured period).
- **FR-003**: The system MUST register MACD as a strategy with canonical `strategy_id` = `macd`, display name "MACD", parameters: `fastPeriod` (integer, default 12, min 1), `slowPeriod` (integer, default 26, min 2), `signalPeriod` (integer, default 9, min 1). Cross-field constraint: `fastPeriod` MUST be less than `slowPeriod` — message: "Fast period must be less than slow period."
- **FR-004**: MACD MUST emit BUY on bullish crossover (MACD line crosses from at/below to above the signal line), SELL on bearish crossover (from at/above to below), and HOLD otherwise. MACD MUST emit HOLD during warm-up.
- **FR-005**: The system MUST register Bollinger Bands as a strategy with canonical `strategy_id` = `bollinger_bands`, display name "Bollinger Bands", parameters: `period` (integer, default 20, min 2), `stdDev` (decimal_string, default `"2.0"`, must be > 0). No cross-field constraint.
- **FR-006**: Bollinger Bands MUST emit BUY when the current close crosses from below the lower band (SMA − stdDev × σ) to at/above it, SELL when the current close crosses from above the upper band (SMA + stdDev × σ) to at/below it, and HOLD otherwise — including while close remains outside a band without recovering across it. MUST emit HOLD during warm-up.
- **FR-007**: The system MUST register Breakout as a strategy with canonical `strategy_id` = `breakout`, display name "Breakout", parameters: `lookback` (integer, default 20, min 2). No cross-field constraint.
- **FR-008**: Breakout MUST emit BUY whenever the current close exceeds the highest close of the prior `lookback` bars, SELL whenever it falls below the lowest close of those bars, and HOLD otherwise. Consecutive bars that keep making new extremes MUST each emit BUY or SELL respectively (trend-following continuation; not first-break-only). MUST emit HOLD during warm-up.
- **FR-009**: Each new strategy MUST declare `min_history_candles` = `S` using these formulas: RSI `S = period`; MACD `S = slowPeriod + signalPeriod` (conventional lower bound for this feature; not a claim of perfect MACD seed maturity); Bollinger Bands `S = period`; Breakout `S = lookback`. Backtest MUST reject with `insufficient_history` when closed-candle count &lt; `S`. When count ≥ `S` but &lt; `S+1`, and during warm-up until `S+1` candles are available, the strategy MUST emit HOLD. From `S+1` onward, crossover strategies MAY evaluate using current and previous indicator state. This matches Dual EMA’s Feature 005 contract: `S` is enough history to accept the backtest; `S+1` is enough to make a crossover decision.
- **FR-010**: Each new strategy MUST implement the shared `Strategy` protocol from `app.strategy.base` (receive `Sequence[CandleClose]`, return `StrategySignal`). Strategies MUST NOT execute trades, place orders, or modify balances/positions.
- **FR-011**: `GET /strategies` MUST return all registered strategies (Dual EMA + RSI + MACD + Bollinger Bands + Breakout) with their parameter schemas, defaults, and constraints.
- **FR-012**: Simulation and Backtest create, pipeline, and engine MUST support the new strategy ids through the existing registry resolve/validate/materialize path without special-casing. No strategy-specific branches in API or engine code.
- **FR-013**: Existing Dual EMA behavior, continuity tests, and configuration MUST remain unchanged. Dual EMA's canonical id, alias, defaults, warm-up, and signal semantics are not altered by this feature.
- **FR-014**: Strategy UI (StrategyConfigFields) MUST dynamically render parameter fields for the selected strategy based on registry data, without hard-coding fields for any specific strategy.
- **FR-015**: This feature MUST NOT enable real-money trading, leverage, shorting, strategy optimization, auto-ranking, ML, multi-strategy, or sentiment signals.

### Key Entities

- **StrategyDefinition (registry entry)**: One per strategy — canonical id, display name, aliases, parameter schema, constraints, factory, validate function. Four new entries alongside Dual EMA.
- **Strategy parameters**: RSI (`period`, `overbought`, `oversold`), MACD (`fastPeriod`, `slowPeriod`, `signalPeriod`), Bollinger Bands (`period`, `stdDev`), Breakout (`lookback`). Persisted as JSON on session/run rows via existing `strategy_params` column.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `GET /strategies` returns exactly 5 strategies with correct schemas when all are registered.
- **SC-002**: An operator can select any of the four new strategies on Simulation and Backtest forms, see editable parameters with defaults, and start a session/backtest that persists the chosen strategy and parameters.
- **SC-003**: On fixed closed-candle fixtures, each new strategy's signal sequence (BUY/SELL/HOLD per bar) is deterministic and matches the documented algorithm (locked golden tests).
- **SC-004**: Invalid parameters for any new strategy are rejected on create with a clear constraint message (e.g. oversold ≥ overbought for RSI).
- **SC-005**: Dual EMA continuity tests from Feature 005 still pass without modification after all new strategies are registered.
- **SC-006**: Each new strategy’s `S` (`min_history_candles`) drives backtest `insufficient_history` when count &lt; `S`, HOLD at count = `S`, and crossover-eligible evaluation from `S+1`, matching Dual EMA’s Feature 005 contract.

## Assumptions

- The existing strategy framework from Feature 005 is fully implemented and converged (registry, shared contract, `StrategyConfigFields` dynamic rendering, `strategy_params` column, `GET /strategies`, `validate_and_materialize`).
- Dual EMA Feature 005 history contract is reused: `S` = accept gate; `S+1` = first bar where a prior indicator state exists for crossover. Per-strategy `S`: RSI=`period`; MACD=`slowPeriod + signalPeriod` (accepted conventional bound for this feature); Bollinger=`period`; Breakout=`lookback`.
- RSI uses a standard Wilder's smoothing (exponential moving average of gains/losses).
- MACD uses standard EMA-based computation (fast EMA − slow EMA = MACD line; EMA of MACD line = signal line). Exact EMA seeding beyond the shared `S` / `S+1` contract may be refined later without changing that contract.
- Bollinger Bands use a simple moving average (SMA) with population standard deviation.
- Breakout uses a simple highest/lowest of closes over the prior lookback window (current bar excluded). It is trend-following: every new extreme beyond that window emits BUY or SELL; this is intentional continuation signaling, distinct from RSI/Bollinger recovery mean-reversion.
- Cross-bar comparisons use current vs previous bar values (same event style as Dual EMA). RSI and Bollinger Bands specifically use recovery crossovers (out of oversold / out of overbought; back through lower / upper band), not sustained level signals while outside those zones.
- All computations use Python `Decimal` for consistency with existing money/indicator handling.
- `StrategyConfigFields` already dynamically renders from `GET /strategies` parameter schemas — no UI hard-coding needed for new strategies.
- Each strategy file auto-registers on import (same pattern as `dual_ema.py`).
