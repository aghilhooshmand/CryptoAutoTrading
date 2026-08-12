# Feature Specification: Strategy Comparison and Evaluation

**Feature Branch**: `007-strategy-comparison`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Feature 007 — Strategy Comparison and Evaluation: Allow the operator to compare multiple registered strategies fairly over the same historical market data and backtest configuration. The operator selects trading pair, timeframe, historical start/end, starting capital, allocated capital, max position size, fee/slippage, optional common risk limits, and two or more registered strategies. The system runs each selected strategy independently against the exact same normalized historical candle series and financial assumptions. Each strategy keeps its own configured parameters. Show a comparison including at minimum: net P&L, return %, maximum drawdown, win rate, round-trip count / fill count, total fees, total slippage, best/worst trade, buy-and-hold return, difference versus buy-and-hold. Allow the operator to inspect the underlying individual backtest result for each strategy. Do not automatically declare a strategy \"best\" based only on return. Do not perform parameter optimization, grid search, automatic strategy selection, ML, walk-forward testing, or real-money trading. Comparison must reuse the existing Feature 004 backtesting engine and Feature 005/006 strategy registry rather than implementing separate strategy or accounting logic."

## Clarifications

### Session 2026-08-12

- Q: What is the maximum number of strategy legs allowed in a single comparison run? → A: Hard max of 5 legs; same strategy id may appear more than once with different params (minimum remains 2).
- Q: Should each comparison leg’s underlying backtest also appear in the normal single-strategy backtest history list? → A: Each leg is persisted as a normal backtest run and remains fully inspectable, but is marked as originating from a comparison and can be filtered/hidden from the main backtest history view.
- Q: Should a multi-strategy comparison finish all legs in one request before showing results, or create a comparison that operators refresh until complete? → A: Synchronous — historical candles are fetched once and shared across all 2–5 legs; the request returns only after all legs are evaluated and the comparison reaches its final state; no polling, background worker, WebSocket progress, or asynchronous comparison jobs in v1.
- Q: How many completed and failed strategy comparisons should the system keep available for later inspection? → A: Keep the latest 10 completed comparisons and latest 5 failed comparisons (FIFO, oldest first). Underlying leg backtests continue to follow Feature 004 retention rules and remain linked where still available.
- Q: Must the comparison table show both round-trip count and fill count for every leg, or is one of those activity metrics enough? → A: Every comparison leg must report both roundTripCount and fillCount as separate metrics (fill count = execution activity; round-trip count = completed trading cycles).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a fair multi-strategy comparison (Priority: P1)

An operator under Auto Trading configures one shared historical window and shared financial assumptions, selects two or more registered strategies (each with its own parameters), runs a comparison, and sees a side-by-side results table so they can evaluate relative outcomes on identical market data without claiming a single “winner.”

**Why this priority**: Fair apples-to-apples comparison is the core value of this feature; without a completed multi-leg run and summary table there is no MVP.

**Independent Test**: Select pair, timeframe, start/end, capital nesting, fee/slippage, and at least two registered strategies with valid params; run comparison; receive one completed comparison whose rows share the same market window and money assumptions and differ only by strategy identity and that strategy’s parameters.

**Acceptance Scenarios**:

1. **Given** Auto Trading comparison configuration, **When** the operator provides a valid shared backtest setup and selects two or more registered strategies (at most five), **Then** the system fetches the shared historical series once, runs each selected strategy independently on that series under shared financial assumptions, and returns only after the comparison reaches a final completed or failed state (no async polling in v1).
2. **Given** a completed comparison, **When** the operator views the comparison summary, **Then** each strategy row shows at least: net P&L, return %, maximum drawdown, win rate, round-trip count, fill count, total fees, total slippage, best trade, worst trade, buy-and-hold return, and difference versus buy-and-hold.
3. **Given** the comparison UI or summary, **When** the operator looks for an automatic “best strategy” label based only on return, **Then** no such automatic declaration is present (operators may still sort or scan metrics themselves).
4. **Given** required shared inputs are missing or invalid, fewer than two strategies are selected, more than five legs are selected, an unknown strategy is selected, or any selected strategy’s parameters are invalid, **When** the operator attempts to run, **Then** the system rejects the comparison with a clear reason and does not invent partial leaderboard results.

---

### User Story 2 - Inspect each strategy’s underlying backtest (Priority: P1)

After a comparison completes, the operator opens any strategy’s individual backtest result (summary, trades, decisions) to understand why that row looks the way it does, using the same inspect surfaces as a single Feature 004 backtest. Each leg is stored as a normal backtest run marked as originating from a comparison, so it can be filtered or hidden in the main backtest history while remaining fully inspectable from the comparison.

**Why this priority**: Comparison numbers alone are not enough for trustworthy evaluation; drill-down into journals is required for evidence-based review.

**Independent Test**: Complete a two-strategy comparison; open the detail for strategy A and strategy B; confirm each detail matches that strategy’s independent backtest on the shared window; confirm each leg is marked as comparison-originated and can be hidden from the default main backtest history view.

**Acceptance Scenarios**:

1. **Given** a completed comparison, **When** the operator chooses to inspect one strategy’s underlying result, **Then** they see that strategy’s individual backtest summary and journals (trades and decisions) for the shared configuration.
2. **Given** two strategies in the same comparison, **When** the operator inspects each in turn, **Then** each underlying result is independent (separate fills and decisions) while sharing the same pair, timeframe, window, and financial assumptions.
3. **Given** completed comparison legs, **When** the operator views the main backtest history with comparison-originated runs filtered/hidden, **Then** those legs do not clutter the default list, yet remain reachable and fully inspectable from the comparison (and when the filter includes them).
4. **Given** a completed comparison leg, **When** the operator inspects it, **Then** it is identifiable as originating from a comparison (not a standalone manual backtest).

---

### User Story 3 - Configure per-strategy parameters under shared market assumptions (Priority: P2)

The operator keeps one shared market and money setup, but edits each selected strategy’s own parameters (for example Dual EMA periods vs RSI thresholds) before running, so comparison reflects intentional strategy configuration rather than forcing identical parameter schemas.

**Why this priority**: Useful once multi-run works; strategies have different parameter shapes and must remain individually configurable.

**Independent Test**: Select RSI and Dual EMA; set distinct valid params for each; run; confirm each row’s effective parameters match what was configured for that strategy.

**Acceptance Scenarios**:

1. **Given** two or more strategies selected, **When** the operator edits parameters for one strategy, **Then** other strategies’ parameters are unchanged.
2. **Given** invalid parameters for any one selected strategy, **When** the operator submits the comparison, **Then** the run is rejected with that strategy’s constraint message before results are produced.

---

### User Story 4 - Apply optional common risk limits to every leg (Priority: P2)

The operator optionally sets common historical risk limits (such as optional profit target, maximum loss, and/or maximum trades, consistent with Feature 004 backtest options) once; every strategy leg in the comparison uses those same optional limits.

**Why this priority**: Shared risk limits keep the comparison fair when early-exit or trade-cap rules matter; optional so simple comparisons remain easy.

**Independent Test**: Run the same two strategies twice—once with an optional max-trades limit and once without—and confirm the limit applies equally to both legs when set.

**Acceptance Scenarios**:

1. **Given** optional common risk limits are omitted, **When** the comparison runs, **Then** no strategy leg is constrained by those omitted limits (same as Feature 004 when those inputs are omitted).
2. **Given** optional common risk limits are set, **When** the comparison runs, **Then** every selected strategy leg uses the same limit values under the shared capital and fee/slippage assumptions.

---

### Edge Cases

- Fewer than two strategies selected → reject; comparison is not a single-strategy backtest substitute (use Feature 004 for one strategy).
- More than five legs selected → reject with a clear reason.
- Duplicate strategy id on more than one leg with different params → allowed (each selection is a distinct comparison leg), subject to the overall maximum of five legs.
- History window too short for the strictest selected strategy’s minimum history requirement → reject the comparison with a clear insufficient-history reason (no silent truncation; no fabricated candles).
- History window oversized per Feature 004 maximum load rules → reject before run with a clear oversized-history reason.
- One strategy fails after accept while others succeed → treat as comparison failure for fairness (do not publish a partial leaderboard that mixes completed and failed legs); surface the failure reason. Because execution is synchronous, the operator receives that final failed state from the same request.
- Unknown or unregistered strategy id → reject.
- Buy-and-hold return is computed once from the shared window and shared cost assumptions and shown consistently for difference-versus-buy-and-hold on every strategy row.
- When a comparison is evicted by retention, previously linked leg backtests are not automatically deleted by the comparison retention rule; they continue under Feature 004 backtest retention (and may become unlinkable from an evicted comparison once that comparison record is gone).
- Real-money trading, live orders, optimization, grid search, automatic strategy selection, ML, and walk-forward testing remain unavailable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the operator to configure a strategy comparison with shared inputs: trading pair, timeframe, historical start and end, starting capital, allocated capital, max position size, fee rate, slippage rate, and optional common risk limits consistent with Feature 004 backtest options.
- **FR-002**: The system MUST require selection of at least two and at most five comparison legs. Each leg MUST identify a registered strategy (Feature 005/006 catalog) and that leg’s strategy parameters. The same strategy id MAY appear on more than one leg with different parameters.
- **FR-003**: The system MUST run each selected leg independently against the exact same normalized historical candle series and the same shared financial assumptions (capital nesting, fees, slippage, optional common risk limits). Strategies MUST NOT share positions, fills, or account state across legs. Historical candles MUST be fetched once per comparison and shared across all legs.
- **FR-003a**: Comparison execution MUST be synchronous in v1: the create/run request MUST return only after all legs have been evaluated and the comparison has reached a final state (completed or failed). The system MUST NOT require polling, a background worker, WebSocket progress, or asynchronous comparison jobs for this feature.
- **FR-004**: Each leg MUST use its own configured strategy parameters and MUST resolve through the existing strategy registry (no duplicate strategy implementations and no comparison-only signal logic).
- **FR-005**: Comparison execution MUST reuse the existing Feature 004 backtesting engine and accounting semantics for each leg (including controller/risk authority, fill rules, net P&L, journals, and buy-and-hold methodology already established for backtests). The feature MUST NOT invent a separate strategy evaluator or separate money ledger for comparison.
- **FR-006**: For each completed leg, the comparison summary MUST present at least: net P&L, return %, maximum drawdown, win rate, round-trip count, fill count, total fees, total slippage, best trade, worst trade, buy-and-hold return, and difference versus buy-and-hold. Round-trip count and fill count are separate required metrics (fill count measures execution activity; round-trip count measures completed trading cycles).
- **FR-007**: The operator MUST be able to open and inspect the underlying individual backtest result for each completed leg (summary plus trade and decision journals). Each completed leg MUST be persisted as a normal backtest run that is marked as originating from a comparison, remains fully inspectable, and MUST be filterable/hideable from the main backtest history view so comparison legs do not clutter standalone history by default.
- **FR-008**: The system MUST NOT automatically declare a strategy (or leg) “best,” “winner,” or equivalent based solely on return % or any single metric.
- **FR-009**: The system MUST reject invalid shared configuration, invalid per-leg parameters, unknown strategy ids, selections with fewer than two legs or more than five legs, oversized history, and insufficient history for the strictest selected leg’s minimum candle requirement, with clear operator-facing reasons.
- **FR-010**: This feature MUST NOT enable parameter optimization, grid search, automatic strategy selection, machine learning, walk-forward testing, or real-money trading.
- **FR-011**: Comparison entry and results MUST remain within the existing Auto Trading area (no new primary navigation area).
- **FR-012**: The system MUST retain at most the latest 10 completed strategy comparisons and the latest 5 failed strategy comparisons, evicting the oldest first when over limit. Underlying leg backtests MUST continue to follow Feature 004 retention rules and MUST remain linked from a comparison while those backtest records are still available.

### Key Entities

- **StrategyComparison**: One comparison job — shared market window, shared financial assumptions, optional common risk limits, ordered list of legs, overall status, and summary rows for completed runs. Retention: latest 10 completed and 5 failed comparisons (FIFO).
- **ComparisonLeg**: One strategy participation — strategy identity, effective parameters, link to that leg’s individual backtest result (a normal backtest run marked as comparison-originated), and summary metrics for the comparison table.
- **SharedMarketWindow**: Pair, timeframe, start/end, and the normalized closed-candle series used by every leg.
- **BuyAndHoldBenchmark**: Single buy-and-hold outcome for the shared window and cost assumptions, used for difference-versus-buy-and-hold on every leg.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can configure and complete a comparison of at least two registered strategies on one shared historical window in a single synchronous submit-and-wait flow under Auto Trading.
- **SC-002**: For a fixed shared candle series and money assumptions, repeating the same comparison configuration produces the same per-leg summary metrics (deterministic evaluation).
- **SC-003**: Every required comparison metric listed in FR-006 is visible for each completed leg without opening that leg’s detail view.
- **SC-004**: From a completed comparison, the operator can open each leg’s underlying backtest detail and verify journals exist for that leg; comparison-originated runs can be filtered/hidden from the default main backtest history without losing inspectability from the comparison.
- **SC-005**: Invalid comparisons (fewer than two legs, more than five legs, bad params, unknown strategy, oversized or insufficient history) are blocked with a clear reason and do not produce a fabricated leaderboard.
- **SC-006**: The comparison experience never shows an automatic “best/winner” designation based only on return; operators remain responsible for interpreting multiple metrics.
- **SC-008**: After more than 10 completed comparisons exist, only the newest 10 remain available; after more than 5 failed comparisons exist, only the newest 5 failed remain available.

## Assumptions

- Feature 004 backtesting core is available (historical candles, engine, summary metrics, journals, buy-and-hold, retention and size limits).
- Feature 005/006 strategy registry is available with at least two registered strategies and dynamic parameter schemas.
- Optional common risk limits mean the same optional Feature 004 backtest controls (for example optional profit target, maximum loss, and maximum trades) applied identically to every leg when provided.
- Capital nesting invariant remains `0 < max_position_size ≤ allocated_capital ≤ starting_capital`, shared across legs.
- Buy-and-hold is computed once for the shared window and shared cost model (Feature 004 methodology), not separately reinvented per strategy algorithm.
- Fairness for minimum history: the shared window must satisfy the strictest selected leg’s minimum closed-candle requirement; otherwise the comparison is rejected.
- If any leg fails after the comparison has been accepted, the comparison is marked failed rather than showing a mixed completed/failed leaderboard.
- Comparison UX lives under Auto Trading alongside existing backtest controls; single-strategy Feature 004 backtests remain available unchanged.
- Comparison legs are normal persisted backtest runs marked as comparison-originated; the main history view can filter/hide them by default while the comparison keeps direct links.
- A comparison includes at least 2 and at most 5 legs; duplicate strategy ids across legs are allowed when parameters differ.
- Comparison runs are synchronous: one shared candle fetch, all legs evaluated before the response returns; no async comparison jobs in v1.
- Operators may sort or visually scan the metrics table; sorting is not an automatic endorsement of a “best” strategy.
- Retention of comparison records: latest **10 completed** and **5 failed** comparisons (FIFO oldest first). Leg backtests follow Feature 004 retention independently and stay linked from the comparison while still available.
- No concurrent multi-user access; local single-operator use.
