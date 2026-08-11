# Feature Specification: Strategy Framework and Selection

**Feature Branch**: `005-strategy-framework`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Feature 005 — Strategy Framework and Selection: make trading strategies pluggable and selectable while preserving Controller → Risk → Execution; common strategy contract over normalized closed candles returning BUY/SELL/HOLD only; strategy registry with stable strategy_id and validated parameters; Simulation and Backtest select the same registered Dual EMA 9/21 implementation; persist selection; fail safely on unknown/invalid; UI selection under Auto Trading; no real trading; out of scope: many new strategies, optimization, auto-selection, ranking, ML, multi-strategy, sentiment."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a registered strategy for simulation (Priority: P1)

An operator starting a local simulation session under Auto Trading can see the registered strategies, select one (initially Dual EMA 9/21), review or adjust that strategy’s declared parameters, and start the session with the chosen strategy and parameters stored on the session. Strategy signals remain advisory only; Controller and Risk continue to decide approval, and the strategy never places trades or changes balances.

**Why this priority**: Simulation is the live proving ground; selectable strategies without breaking the controlled pipeline is the core of this feature.

**Independent Test**: Create a simulation session selecting Dual EMA with default parameters, confirm the session records that strategy, and observe that closed-candle evaluation still produces only BUY/SELL/HOLD through the existing control path.

**Acceptance Scenarios**:

1. **Given** Auto Trading Simulation is available, **When** the operator opens session configuration, **Then** they can select from the registered strategies and see Dual EMA 9/21 as an available option.
2. **Given** Dual EMA is selected with its default parameters, **When** the operator starts a valid simulation session, **Then** the session persists the selected strategy identifier and parameters and runs using that strategy.
3. **Given** a non-HOLD signal from the selected strategy, **When** the candle is processed, **Then** Controller and Risk still may approve or reject it, and balances change only through the existing execution path—not by the strategy itself.
4. **Given** required capital/session bounds are otherwise valid, **When** the operator submits an unknown strategy identifier or parameters that fail the strategy’s declared rules, **Then** the system refuses to create the session with a clear reason and does not start trading.

---

### User Story 2 - Choose the same registered strategy for a backtest (Priority: P1)

An operator configuring a historical backtest under Auto Trading selects a registered strategy (initially Dual EMA 9/21), supplies or accepts its parameters, runs the backtest, and sees that strategy choice and parameters stored with the run. Simulation and backtest use the same Dual EMA implementation and contract—not a forked copy.

**Why this priority**: Historical evaluation must use the identical strategy semantics as simulation; selection must work on both paths for the framework to be real.

**Independent Test**: Run a backtest with Dual EMA selected and defaults applied; confirm the completed run records strategy id and parameters and that Dual EMA behavior matches the pre-migration Dual EMA on an identical fixture series when parameters are the historical defaults.

**Acceptance Scenarios**:

1. **Given** Auto Trading Backtest configuration, **When** the operator configures a run, **Then** they can select a registered strategy and Dual EMA 9/21 is available.
2. **Given** Dual EMA with default parameters and a valid history window, **When** the backtest completes, **Then** the run’s stored configuration includes the strategy identifier and parameters used.
3. **Given** the same Dual EMA defaults and the same closed-candle fixture used before this feature, **When** a backtest runs after migration, **Then** signals and fill outcomes attributable to the strategy match the prior Dual EMA behavior (no silent fork).
4. **Given** an unknown strategy id or invalid parameters, **When** the operator attempts to run, **Then** the system rejects before accepting the run with a clear reason (no fabricated results).

---

### User Story 3 - Inspect which strategy ran (Priority: P2)

After a simulation session or backtest run exists, the operator can see which strategy and which parameter values were used, so results are interpretable and comparable later.

**Why this priority**: Persistence and inspectability close the loop after selection; secondary to being able to run correctly.

**Independent Test**: Open a saved/completed backtest or an active/stopped simulation session and confirm strategy id and parameters are visible without needing to remember the create form.

**Acceptance Scenarios**:

1. **Given** a completed backtest that selected Dual EMA, **When** the operator inspects that run, **Then** the strategy identifier and the parameter values used for that run are visible.
2. **Given** a simulation session created with a selected strategy, **When** the operator views session status or detail, **Then** the strategy identifier and parameters for that session are visible.
3. **Given** strategy selection was persisted, **When** the backend restarts, **Then** stored sessions/runs still report the same strategy id and parameters (within existing retention rules).

---

### Edge Cases

- Unknown `strategy_id` on create → reject; do not fall back silently to Dual EMA.
- Missing required strategy parameter → reject with a clear validation reason.
- Parameter outside declared bounds or wrong type → reject.
- Empty strategy registry (should not occur in product builds) → create flows cannot start; surface a clear unavailable reason.
- Strategy emits only BUY / SELL / HOLD; any other outcome is treated as invalid and must not execute.
- HOLD → no balance or position change from that signal.
- Mid-session or mid-run strategy switching is not supported; selection is fixed at create/start of that session or backtest.
- Listing strategies when Dual EMA is the only registration → list contains exactly that one selectable strategy with its parameter definitions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a common strategy contract: strategies receive normalized closed-candle history/state for the configured timeframe and MUST return only BUY, SELL, or HOLD for the latest evaluated closed candle.
- **FR-002**: Strategies MUST NOT execute trades, place orders, or modify cash, positions, or session/backtest balances. Strategy output is advisory input to Controller → Risk → Execution only.
- **FR-003**: The system MUST provide a strategy registry of available strategies, each identified by a stable `strategy_id`.
- **FR-004**: Each registered strategy MUST declare its parameters (names, types/meaning, defaults, and validation rules). The system MUST validate submitted parameters against that declaration before accepting a simulation session or backtest run.
- **FR-005**: The product MUST register Dual EMA 9/21 as the initial strategy (`strategy_id` stable, e.g. `dual_ema_9_21`) with parameters and defaults that preserve existing Dual EMA 9/21 behavior when defaults are used.
- **FR-006**: Simulation session creation MUST require selecting a registered `strategy_id` and MUST accept (and validate) that strategy’s parameters; the chosen id and parameters MUST be persisted with the session.
- **FR-007**: Backtest run creation MUST require selecting a registered `strategy_id` and MUST accept (and validate) that strategy’s parameters; the chosen id and parameters MUST be persisted with the run.
- **FR-008**: Simulation and Backtest MUST resolve and execute the **same** registered strategy implementation for a given `strategy_id` (no separate Dual EMA fork for backtest).
- **FR-009**: After migration, Dual EMA with default parameters MUST produce the same signal semantics on identical closed-candle inputs as before this feature (behavioral continuity).
- **FR-010**: Unknown `strategy_id` or invalid parameters MUST fail safely: refuse create/start of the session or backtest with a clear operator-facing reason; MUST NOT start trading or invent results.
- **FR-011**: Auto Trading Simulation and Backtest UIs MUST allow selecting a registered strategy and editing that strategy’s declared parameters (within validation), without adding a fourth primary navigation area.
- **FR-012**: Operators MUST be able to inspect the strategy id and parameters associated with an existing simulation session and with a completed or failed backtest run (as retained by existing product rules).
- **FR-013**: The system MUST expose enough registry information for the UI to render selection and parameter fields (strategy id, display name, parameter definitions including defaults and constraints).
- **FR-014**: This feature MUST NOT enable or change real-money trading; real orders and trading credentials remain out of scope and unavailable.
- **FR-015**: Strategy evaluation MUST continue to occur only on newly closed candles for the configured timeframe; strategies MUST NOT evaluate the same closed candle twice within a session or backtest run.

### Key Entities

- **Strategy Definition**: A registered strategy with stable `strategy_id`, human-readable name, parameter schema (definitions, defaults, validation), and the shared evaluation behavior used by both simulation and backtest.
- **Strategy Parameters**: The concrete parameter values chosen for one session or backtest (e.g. Dual EMA periods), validated against the strategy’s schema and persisted with that session/run.
- **Strategy Signal**: Advisory BUY, SELL, or HOLD for one closed candle, optionally with diagnostic fields (e.g. indicator values, reason codes) that never confer execution authority.
- **Simulation Session / Backtest Run**: Existing product entities extended to record selected `strategy_id` and validated parameters used for that lifecycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can create a simulation session and a backtest run selecting Dual EMA with defaults in under 2 minutes each (excluding market-data wait and long backtest runtime).
- **SC-002**: 100% of simulation and backtest creates that omit a registered strategy or supply unknown/invalid strategy input are blocked with an understandable reason before any trading or fabricated historical results begin.
- **SC-003**: On a fixed closed-candle fixture, Dual EMA with default parameters after migration matches pre-migration Dual EMA signal sequence (BUY/SELL/HOLD per candle) for that fixture.
- **SC-004**: For any approved non-HOLD path in simulation or backtest, the strategy itself never directly changes balances; 100% of fund/position changes still occur only after Controller and Risk handling through the existing execution path.
- **SC-005**: After create, operators can identify which strategy and parameter values were used for that session or backtest without re-entering the create form (visible on detail/summary surfaces).
- **SC-006**: With only Dual EMA registered, the selectable strategy list shown in Simulation and Backtest contains exactly that strategy and does not invent additional strategies.

## Assumptions

- Target operators are local developers/operators of the existing Auto Trading product (Feature 003 simulation + Feature 004 backtest).
- Dual EMA remains the only registered strategy in the initial delivery; the framework exists so additional strategies can be added later without redesigning the pipeline.
- Dual EMA parameters are the existing periods (fast 9, slow 21) as defaults; they are declared in the registry and may be adjusted by the operator subject to validation (e.g. positive integers, fast period strictly less than slow period). Default values preserve prior behavior.
- Strategy selection is fixed when a simulation session or backtest run is created; changing strategy mid-session or mid-run is out of scope.
- Existing Controller, Risk, sizing, fees/slippage, long-only full-position model, and Feature 004 historical fill timing remain unchanged by this feature except for how the strategy instance is resolved.
- Listing/selecting strategies does not require exchange trading credentials.
- Display names may be localized or static English in v1; `strategy_id` values are stable machine identifiers.
- Persisted strategy fields follow existing session/backtest retention and storage lifetimes already defined by Features 003 and 004.

## Out of Scope

- Shipping many new strategies beyond Dual EMA 9/21 in this feature
- Strategy optimization, grid search, or parameter sweeps
- Automatic strategy selection or ranking
- Machine-learning strategies
- Combining multiple strategies in one session/run
- Sentiment, news, or external signal feeds as strategy inputs
- Real-money trading enablement or XT private order placement
- Mid-session/mid-run hot-swapping of strategies
- A fourth primary navigation area for strategies
