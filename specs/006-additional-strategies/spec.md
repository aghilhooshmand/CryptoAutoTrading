# Feature Specification: Additional Strategies

**Feature Branch**: `006-additional-strategies`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Feature 006 — Additional Strategies: add RSI, MACD, Bollinger Bands, and Breakout to the existing strategy framework. Each implements the shared strategy contract, registers via the registry, exposes parameters with defaults and validation, returns BUY/SELL/HOLD only, and works identically in Simulation and Backtest. Keep strategies simple and deterministic. No optimization, ranking, ML, multi-strategy, sentiment, leverage, shorting, or real-money trading."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select RSI for simulation and backtest (Priority: P1)

An operator configuring a simulation or backtest under Auto Trading sees RSI in the strategy selector alongside Dual EMA, can accept defaults (period 14, overbought 70, oversold 30) or edit valid parameters, and run a session or backtest that evaluates RSI signals through the existing Controller → Risk → Execution pipeline.

**Why this priority**: RSI is the most widely recognized momentum oscillator; adding it first validates that the framework supports a second strategy type end-to-end without breaking Dual EMA.

**Independent Test**: Create a simulation session with `strategyId: rsi` and default parameters; confirm session persists `rsi` + effective params; run a backtest with custom thresholds (overbought 75, oversold 25); confirm signals match RSI semantics (BUY below oversold, SELL above overbought, HOLD otherwise).

**Acceptance Scenarios**:

1. **Given** Auto Trading strategy selector, **When** the operator opens session/backtest configuration, **Then** RSI appears as a selectable strategy with default parameters displayed.
2. **Given** RSI selected with valid parameters, **When** the session/backtest runs on closed candles, **Then** the strategy emits BUY when RSI crosses below the oversold threshold, SELL when RSI crosses above the overbought threshold, and HOLD otherwise.
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

An operator selects Bollinger Bands, accepts defaults (period 20, standard deviations 2.0) or edits, and runs. The strategy emits BUY when price closes below the lower band (mean reversion entry), SELL when price closes above the upper band (mean reversion exit/overbought), and HOLD otherwise.

**Why this priority**: Bollinger Bands offer a volatility-based mean-reversion approach, widening the strategy type diversity beyond pure trend-following.

**Independent Test**: Create a simulation with `strategyId: bollinger_bands` and defaults; verify BUY/SELL thresholds correspond to standard deviation bands around the moving average.

**Acceptance Scenarios**:

1. **Given** Bollinger Bands with defaults (20, 2.0), **When** price closes below the lower band, **Then** signal is BUY.
2. **Given** price closes above the upper band, **Then** signal is SELL.
3. **Given** price is within the bands, **Then** signal is HOLD.
4. **Given** invalid parameters (e.g. period < 2, stdDev ≤ 0), **When** operator submits, **Then** rejected with a clear message.

---

### User Story 4 - Select Breakout for simulation and backtest (Priority: P2)

An operator selects Breakout, accepts defaults (lookback 20) or edits, and runs. The strategy emits BUY when the current close exceeds the highest close of the prior lookback window, SELL when it falls below the lowest close, and HOLD otherwise.

**Why this priority**: Breakout is a classic channel/range strategy that rounds out the initial set with a momentum/volatility breakout approach.

**Independent Test**: Create a backtest with `strategyId: breakout` and a lookback of 10; confirm BUY/SELL at known highs/lows of a crafted fixture.

**Acceptance Scenarios**:

1. **Given** Breakout with lookback 20, **When** current close exceeds the prior 20-bar high, **Then** signal is BUY.
2. **Given** current close falls below the prior 20-bar low, **Then** signal is SELL.
3. **Given** close is within the prior range, **Then** signal is HOLD.
4. **Given** lookback < 2, **When** operator submits, **Then** rejected.

---

### Edge Cases

- Selecting any new strategy with insufficient history for that strategy's minimum requirement → backtest fails with `insufficient_history`; simulation emits HOLD during warm-up.
- Dual EMA behavior unchanged after new strategies are registered (existing tests and continuity fixture still pass).
- Unknown `strategy_id` still rejected on create and START/RESUME (existing fail-safe unaffected).
- Omitting `strategyId` still rejected (existing FR-006/FR-007 from Feature 005).
- All four new strategies return HOLD when candle count is below their warm-up threshold (no fabricated signals from partial data).
- `GET /strategies` returns all five strategies (Dual EMA + four new) with parameter schemas.
- Strategy parameters persisted and visible on session/backtest inspect surfaces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register RSI as a strategy with canonical `strategy_id` = `rsi`, display name "RSI", parameters: `period` (integer, default 14, min 2), `overbought` (integer, default 70, min 1, max 99), `oversold` (integer, default 30, min 1, max 99). Cross-field constraint: `oversold` MUST be less than `overbought` — message: "Oversold threshold must be less than overbought threshold."
- **FR-002**: RSI MUST emit BUY when the computed RSI value crosses below the `oversold` threshold, SELL when it crosses above the `overbought` threshold, and HOLD otherwise. RSI MUST emit HOLD during warm-up (insufficient history for the configured period).
- **FR-003**: The system MUST register MACD as a strategy with canonical `strategy_id` = `macd`, display name "MACD", parameters: `fastPeriod` (integer, default 12, min 1), `slowPeriod` (integer, default 26, min 2), `signalPeriod` (integer, default 9, min 1). Cross-field constraint: `fastPeriod` MUST be less than `slowPeriod` — message: "Fast period must be less than slow period."
- **FR-004**: MACD MUST emit BUY on bullish crossover (MACD line crosses from at/below to above the signal line), SELL on bearish crossover (from at/above to below), and HOLD otherwise. MACD MUST emit HOLD during warm-up.
- **FR-005**: The system MUST register Bollinger Bands as a strategy with canonical `strategy_id` = `bollinger_bands`, display name "Bollinger Bands", parameters: `period` (integer, default 20, min 2), `stdDev` (decimal_string, default `"2.0"`, must be > 0). No cross-field constraint.
- **FR-006**: Bollinger Bands MUST emit BUY when the current close is below the lower band (SMA − stdDev × σ), SELL when above the upper band (SMA + stdDev × σ), and HOLD otherwise. MUST emit HOLD during warm-up.
- **FR-007**: The system MUST register Breakout as a strategy with canonical `strategy_id` = `breakout`, display name "Breakout", parameters: `lookback` (integer, default 20, min 2). No cross-field constraint.
- **FR-008**: Breakout MUST emit BUY when the current close exceeds the highest close of the prior `lookback` bars, SELL when below the lowest close, and HOLD otherwise. MUST emit HOLD during warm-up.
- **FR-009**: Each new strategy MUST declare its `min_history_candles` requirement. Backtest insufficient-history checks and simulation warm-up HOLD behavior MUST use this value, consistent with Dual EMA's `S` semantics from Feature 005.
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
- **SC-006**: Each new strategy's `min_history_candles` drives backtest insufficient-history rejection and simulation warm-up HOLD correctly.

## Assumptions

- The existing strategy framework from Feature 005 is fully implemented and converged (registry, shared contract, `StrategyConfigFields` dynamic rendering, `strategy_params` column, `GET /strategies`, `validate_and_materialize`).
- RSI uses a standard Wilder's smoothing (exponential moving average of gains/losses).
- MACD uses standard EMA-based computation (fast EMA − slow EMA = MACD line; EMA of MACD line = signal line).
- Bollinger Bands use a simple moving average (SMA) with population standard deviation.
- Breakout uses a simple highest-high / lowest-low of closes over the lookback window.
- "Crosses below/above" semantics mirror Dual EMA: compare current vs previous bar values.
- All computations use Python `Decimal` for consistency with existing money/indicator handling.
- `StrategyConfigFields` already dynamically renders from `GET /strategies` parameter schemas — no UI hard-coding needed for new strategies.
- Each strategy file auto-registers on import (same pattern as `dual_ema.py`).
