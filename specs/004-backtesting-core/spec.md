# Feature Specification: Backtesting Core

**Feature Branch**: `004-backtesting-core`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Feature 004 — Backtesting Core: deterministic historical backtesting of the existing Dual EMA strategy against normalized market candles, reusing Feature 003 trading semantics (controller/risk authority, long-only full position, sizing, fees/slippage, Decimal accounting), with inspectable results including net P&L, trade stats, drawdown, and buy-and-hold comparison; shared strategy implementation; no real orders, no WebSockets, no optimization or additional strategies."

## Clarifications

### Session 2026-08-11

- Q: Which price from each closed historical candle should approved simulated fills use? → A: Next candle open — signals from closed Candle N; approved strategy fills use Candle N+1 open (+ fee/slippage); no N+1 → no normal strategy fill; end-of-run flatten uses final processed closed candle close (+ fee/slippage)
- Q: After a backtest finishes, how long should its results stay available for inspection? → A: Persist latest 20 completed runs (config, summary, trades, decisions); survive backend restart; operator can inspect/delete; when over limit, drop oldest completed run
- Q: Should a maximum number of strategy trades be a required backtest input, optional, or omitted in v1? → A: Optional; when set, enforce like Feature 003 (strategy fills only); when omitted, no max-trades cap
- Q: How often should equity be recorded for maximum drawdown during a backtest? → A: After every processed closed candle, record liquidation-consistent equity and compute maximum drawdown from that equity series
- Q: What should happen if the requested history window is larger than the system can load for that timeframe? → A: Enforce a documented maximum candle count (or equivalent max span per timeframe); reject oversized requests before run with a clear reason (no silent truncation)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure and run one historical backtest (Priority: P1)

A developer or operator configures a historical backtest for a supported pair (timeframe, start/end window, capital nesting, fee and slippage rates), runs it against available historical candles, and receives a completed result without placing any real exchange orders and without requiring trading credentials.

**Why this priority**: Without a runnable, bounded backtest, there is no historical proving ground before simulation trading.

**Independent Test**: Configure a valid window and capital bounds for a supported pair and timeframe, run the backtest, and obtain a finished summary with starting/ending capital and net P&L.

**Acceptance Scenarios**:

1. **Given** the application is running locally without exchange trading credentials, **When** the operator configures a valid backtest (pair, timeframe, start/end, capital nesting, fee/slippage; optional max trades and optional profit/loss rates) and runs it, **Then** the system completes one backtest run and returns a result for that configuration.
2. **Given** required inputs are missing or invalid (including violation of `0 < max_position_size ≤ allocated_capital ≤ starting_capital`, end before start, unsupported timeframe, unsupported pair, or a history window that exceeds the documented maximum load size), **When** the operator attempts to run, **Then** the system blocks the run with a clear reason and does not invent results or silently truncate history.
2a. **Given** max trades is omitted, **When** the backtest runs, **Then** strategy fills are not rejected solely for reaching a max-trades limit.
2b. **Given** max trades is set to a positive integer, **When** strategy-driven fills reach that count, **Then** further strategy fills are blocked consistently with Feature 003 while an end-of-run flatten remains allowed if still long.
3. **Given** a completed backtest, **When** the operator views the summary, **Then** starting capital, ending capital, net P&L, and return % are visible and consistent with each other.
4. **Given** the product, **When** the operator looks for real-money or live-order controls on the backtest path, **Then** those remain unavailable/non-functional for this feature.

---

### User Story 2 - Same controlled pipeline as simulation, over history (Priority: P1)

While a backtest runs, the system walks normalized historical closed candles in chronological order, evaluates Dual EMA(9)/EMA(21) once per newly processed closed candle, routes every non-HOLD signal through Trading Controller and Risk Manager, and only then applies simulated fills with the same fee and adverse-slippage model used in Feature 003.

**Why this priority**: Constitutional pipeline integrity and semantic parity with simulation are the point of backtesting before live simulation use.

**Independent Test**: With a fixed historical candle series, observe at least one HOLD with no balance change and at least one approved or rejected non-HOLD path that never bypasses controller/risk.

**Acceptance Scenarios**:

1. **Given** a backtest in progress over closed historical candles, **When** the strategy emits HOLD, **Then** no simulated trade executes and balances/positions do not change from that signal.
2. **Given** a non-HOLD signal valid for the long-only full-position model and a next historical candle exists after the signal candle, **When** control and risk approve it, **Then** a simulated BUY opens a full long from flat, or a simulated SELL fully closes the long, using the **next candle’s open** as the reference price plus documented fee/slippage—never a real exchange order.
2a. **Given** a non-HOLD signal on the last available closed candle in the loaded series (no next candle), **When** control and risk would otherwise approve it, **Then** no normal strategy fill is created from that signal (it cannot execute without a next-candle open).
3. **Given** a non-HOLD signal, **When** control or risk rejects it, **Then** balances and positions remain unchanged by that signal and the rejection is recorded for inspection.
4. **Given** any strategy output, **When** a candle is processed, **Then** the strategy never modifies funds or positions directly, and the same closed candle is never processed twice in that run.
5. **Given** identical backtest inputs and the same historical candle series, **When** the operator runs the backtest twice, **Then** the summary metrics and trade list are identical.

---

### User Story 3 - Inspect trades and performance metrics (Priority: P1)

After a run, the operator can inspect the backtest trade list and performance summary, including win/loss counts, win rate, fees, slippage, maximum drawdown, best/worst trade, and a buy-and-hold return for the same pair and period for comparison.

**Why this priority**: Traceability and comparable outcomes are required to decide whether to use the strategy in simulation.

**Independent Test**: After a run that produces at least one trade (or a clear zero-trade result), open the result view and confirm required summary fields and trade detail are present and internally consistent.

**Acceptance Scenarios**:

1. **Given** a completed backtest with at least one simulated fill, **When** the operator opens trades, **Then** each fill is listed with enough detail to understand side, size, timing context, prices/costs, and whether it was a normal strategy fill or an end-of-run flatten.
2. **Given** a completed backtest, **When** the operator views the summary, **Then** they can see at least: starting capital, ending capital, net P&L, return %, trade count, winning trades, losing trades, win rate, total fees, total slippage, maximum drawdown, best trade, worst trade, and buy-and-hold return for the same pair and period.
3. **Given** a completed backtest with zero strategy fills, **When** the operator views the result, **Then** summary fields remain defined (including zero counts where applicable) and buy-and-hold return is still available when price history exists for the window.
4. **Given** decision outcomes occurred during the run, **When** the operator inspects decision history for that backtest, **Then** HOLD, approved, and rejected outcomes for processed closed candles are available with rejection reasons when rejected.
5. **Given** completed backtests were saved previously, **When** the backend restarts, **Then** those completed runs (up to the retention limit) remain inspectable with their configuration, summary, trades, and decisions.
6. **Given** more than 20 completed backtests would be retained, **When** a new run completes, **Then** the oldest completed run is removed so at most 20 completed runs remain.
7. **Given** a saved completed backtest, **When** the operator deletes it, **Then** that run and its stored configuration, summary, trades, and decisions are no longer available.

---

### User Story 4 - Use backtesting from Auto Trading without a fourth primary area (Priority: P2)

The operator reaches backtesting from the existing Auto Trading primary area (or a clearly related surface under that area), configures/runs/inspects results on phone-width and desktop-width layouts for primary controls, and understands that backtesting is historical evaluation—not live simulation and not real money.

**Why this priority**: Usability and product navigation matter, but only after a correct deterministic engine exists.

**Independent Test**: At ~375px and desktop widths, complete configure → run → view summary/trades without desktop-only gestures for primary controls.

**Acceptance Scenarios**:

1. **Given** the three primary areas remain Dashboard, Auto Trading, and Portfolio, **When** the operator wants to backtest, **Then** they can do so without a new top-level primary navigation area.
2. **Given** a phone-width viewport, **When** the operator configures, runs, and inspects a backtest, **Then** primary controls and core summary/trade entry points remain usable.
3. **Given** backtest UI, **When** compared with simulation controls, **Then** labeling makes historical backtest distinct from a live simulation session.

---

### Edge Cases

- End datetime earlier than or equal to start → reject configuration; do not run.
- No historical candles available for the pair/timeframe/window → fail safely with a clear unavailable/insufficient-history reason; do not invent candles or prices.
- Requested window would exceed the documented maximum candle count (or equivalent max span for that timeframe) → reject before run with a clear oversized-history reason; do not silently truncate or invent bars.
- Partial history (gaps) → do not fabricate missing bars; process only available closed candles in chronological order; if history is insufficient for EMA warm-up, remain in HOLD until warm-up completes without inventing prior bars.
- Same closed candle identity already processed in the run → skip; never double-process.
- BUY while already long → reject as conflicting position state; journal; no balance change.
- SELL while flat → reject as conflicting position state; journal; no balance change.
- Full BUY would exceed allocated capital, max position size, or affordable cash after fees → reject per Feature 003 sizing rules; no silent oversize.
- Violation of `0 < max_position_size ≤ allocated_capital ≤ starting_capital` → reject before run.
- Unsupported timeframe (outside `1m`, `5m`, `15m`, `1h`, `4h`, `1d`) → reject.
- Optional max trades omitted → do not cap strategy fills for that reason.
- Optional max trades set → after strategy fill count reaches the limit, reject further strategy entries; end-of-run flatten still allowed if long.
- Fee/slippage omitted → apply Feature 003 documented defaults (0.10% fee and 0.05% adverse slippage per side); never silently assume zero cost unless the operator explicitly sets zero.
- Backtest ends while still long → flatten once at the **final processed closed candle’s close** using the same fee/slippage model so ending capital and net P&L are determinate (mark this flatten as end-of-run, not a strategy signal).
- Approved strategy signal on Candle N with no Candle N+1 available in the historical series → do not create a normal strategy fill (next-open execution requires a subsequent candle).
- Optional profit-target / max-loss rates provided → evaluate using the same liquidation-based Session NET rule as Feature 003 against derived absolute amounts; if a bound is hit, stop processing further strategy entries for the remainder of the window after applying the shared flatten rules for an open long.
- Optional profit-target / max-loss rates omitted → do not apply those early exits; still enforce capital nesting, position model, and end-of-run flatten.
- Operator runs a backtest while a simulation session is active → allowed; backtest is offline historical evaluation and MUST NOT place real orders or mutate the live simulation session state.
- Operator spam-runs the same configuration → each completed run remains deterministic for identical inputs and candle series; concurrent overlapping runs MUST NOT corrupt each other’s results (at most one in-flight backtest per operator is an acceptable v1 limit if needed for simplicity).
- More than 20 completed runs → after a new completion, remove the oldest completed run so at most 20 remain; deleted runs are gone immediately.
- Exchange-specific candle payloads → MUST NOT appear in backtest domain results; only normalized market-data concepts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a historical backtesting mode that never places real exchange orders and never requires exchange trading credentials.
- **FR-002**: Backtesting MUST consume historical prices/candles only through the existing normalized public market-data boundary; XT-specific representations MUST NOT appear in backtesting domain logic or operator-facing backtest contracts.
- **FR-003**: Backtesting MUST enforce the pipeline: historical Market Data → Strategy Engine → Trading Signal → Trading Controller → Risk Manager → Simulation Execution → Position/Balance → continue or stop. Strategies MUST NOT modify balances or positions directly.
- **FR-004**: The operator MUST be able to configure and run a backtest with at least: trading pair; timeframe one of `1m`, `5m`, `15m`, `1h`, `4h`, `1d`; historical start date/time; historical end date/time; starting capital; allocated capital; max position size; fee rate; slippage rate. Capital sizes MUST satisfy `0 < max_position_size ≤ allocated_capital ≤ starting_capital`.
- **FR-004a**: Maximum strategy trades (`max_trades`) MUST be an **optional** backtest input. When provided, Risk MUST enforce it consistently with Feature 003 (limits strategy-driven fills only; end-of-run flatten may still occur). When omitted, the backtest MUST NOT apply a max-trades cap.
- **FR-004b**: The system MUST enforce a **documented maximum** historical load size for backtests (maximum candle count and/or equivalent maximum span per timeframe). If the configured window would exceed that limit, the system MUST **reject the run before processing** with a clear reason. The system MUST NOT silently truncate history to fit the limit.
- **FR-005**: Target net profit rate and maximum session loss rate MUST be optional backtest inputs. When provided, the system MUST derive absolute threshold amounts from allocated capital (same relationship as Feature 003) and MUST apply them as early-exit bounds using liquidation-based Session NET P&L semantics consistent with Feature 003. When omitted, those early exits MUST NOT apply.
- **FR-006**: Feature 004 MUST use exactly one baseline strategy: Dual EMA crossover with EMA(9) fast and EMA(21) slow on closed candle close prices for the selected timeframe. Signal vocabulary is BUY, SELL, and HOLD only.
- **FR-007**: The Dual EMA strategy implementation used by Feature 003 simulation MUST be reusable by backtesting; Feature 004 MUST NOT ship a separate duplicate Dual EMA implementation.
- **FR-008**: The strategy MUST evaluate only on closed candles processed in chronological order for the backtest window. Still-forming/incomplete candles MUST NOT generate signals. Each closed candle identity MUST be processed at most once per run.
- **FR-008a**: Strategy signals are generated from closed Candle **N**. An approved strategy BUY/SELL MUST use Candle **N+1 open** as the reference execution price, then apply configured adverse slippage and fees. If no next candle (N+1) exists in the historical series, that signal MUST NOT create a normal strategy fill.
- **FR-009**: Feature 004 MUST use the long-only single full-position model: BUY only from flat opens the entire allowed long in one fill (subject to Feature 003 sizing); SELL only while long closes the entire long in one fill. Partial adds/reduces, pyramiding, and short selling MUST NOT be supported.
- **FR-010**: Full-position BUY sizing MUST use the same rules as Feature 003: `affordable_notional = current_cash / (1 + fee_rate)` and `intended_notional = min(affordable_notional, allocated_capital, max_position_size)`.
- **FR-011**: Every non-HOLD signal MUST pass through Trading Controller and Risk Manager before simulated execution. HOLD MUST NOT execute a trade.
- **FR-012**: Simulated execution in backtests MUST apply the same fee and adverse-slippage model as Feature 003 (defaults 0.10% fee and 0.05% adverse slippage per side unless overridden) and MUST update balances/positions deterministically with precise money arithmetic consistent with Feature 003 (no imprecise floating-point money math).
- **FR-013**: Accounting, sizing, and risk/control rules SHOULD reuse shared domain logic with Feature 003 where clean reuse is possible rather than forking incompatible copies.
- **FR-014**: Identical backtest configuration inputs and identical historical candle series MUST produce identical results (summary metrics and trade list).
- **FR-015**: If the backtest is still long after the last processed candle in range (or after an early exit bound), the system MUST perform exactly one end-of-run full simulated close using the **final processed closed candle’s close** as the reference price plus the session fee/slippage assumptions so ending capital is determinate; this flatten MUST be inspectable and distinguished from ordinary strategy fills. End-of-run flatten is the only fill path that uses close instead of next-open.
- **FR-016**: A completed backtest result MUST include at least: starting capital; ending capital; net P&L; return %; trade count; winning trades; losing trades; win rate; total fees; total slippage; maximum drawdown; best trade; worst trade; buy-and-hold return for the same pair and period.
- **FR-017**: Buy-and-hold return MUST be computed for the same pair and backtest window as a comparison baseline using one synthetic full entry at the **open of the candle after the first usable closed candle** in range when a next candle exists (otherwise the first usable closed candle’s close), and one full exit at the **last processed closed candle’s close**, applying the same fee and adverse-slippage assumptions once on entry and once on exit so the comparison is cost-aware and aligned with next-open / end-close execution semantics where applicable.
- **FR-018**: The system MUST expose inspectable backtest trades and decision outcomes (including HOLD and rejections with reasons) for a completed run.
- **FR-018a**: The system MUST persist completed backtest runs so each stored run includes at least its configuration, summary, trades, and decisions. Persisted completed runs MUST survive backend restart. The operator MUST be able to inspect stored runs and delete a stored run. The system MUST retain at most **20** completed runs; when a new completed run would exceed that limit, the **oldest** completed run MUST be removed.
- **FR-019**: Maximum drawdown MUST be computed from an equity series built by recording **liquidation-consistent equity after every processed closed candle** (cash when flat; liquidation equity while long, consistent with Feature 003 hard-limit equity semantics). The summary MUST report that maximum drawdown.
- **FR-020**: Winning/losing trades and win rate MUST be defined on completed round-trips (entry to full exit), not on individual fill legs alone; end-of-run flatten participates in the final round-trip when needed.
- **FR-021**: Backtesting MUST be reachable without adding a fourth primary navigation area; Auto Trading remains the primary home for this capability.
- **FR-022**: Completing this feature MUST NOT introduce: additional strategies; strategy optimization; parameter/grid search; strategy ranking; walk-forward testing; machine learning; sentiment/news-driven trading; portfolio management product scope; WebSockets; real-money execution; futures; margin; leverage; short selling; authenticated/private exchange trading APIs; or multi-user authentication.

### Key Entities

- **Backtest Run**: One bounded historical evaluation with pair, timeframe, window, capital nesting, optional profit/loss rates, fee/slippage, status (e.g. configured/running/completed/failed), and links to results. Completed runs are retained (max 20) with configuration, summary, trades, and decisions until deleted or evicted by age.
- **Backtest Configuration**: Operator inputs that fully determine a run when combined with a fixed historical candle series; stored with each completed run.
- **Historical Candle Series**: Ordered closed OHLC points from the normalized market-data boundary for the selected pair/timeframe/window.
- **Strategy Signal**: BUY, SELL, or HOLD from the shared Dual EMA strategy on a closed candle; advisory only.
- **Control/Risk Decision**: Approve or reject outcome for a non-HOLD signal, with explicit reason when rejected.
- **Backtest Trade**: Deterministic simulated fill (strategy or end-of-run flatten) with fees/slippage; never a real exchange order; stored with the completed run.
- **Backtest Decision Record**: Trace of each processed closed-candle evaluation (HOLD / approved / rejected); stored with the completed run.
- **Backtest Summary**: Aggregate performance metrics required by FR-016, including buy-and-hold comparison and maximum drawdown; stored with the completed run.
- **Equity Point**: Liquidation-consistent equity recorded after each processed closed candle; the ordered series is the sole input for maximum drawdown.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator following project docs can configure and complete one Dual EMA backtest for a supported pair and window in under 20 minutes (tools already installed), with no exchange trading credentials.
- **SC-002**: For a fixed fixture candle series and configuration, two consecutive runs produce 100% identical summary metric values and trade lists (bit-for-bit equality of reported decimal strings and counts).
- **SC-003**: In a successful demo path, at least one non-HOLD signal is processed through control/risk such that the outcome is either an approved simulated trade or an explicit rejection—never a silent strategy-to-balance write.
- **SC-004**: After a run that includes at least one HOLD and at least one rejection (when such outcomes occur in the fixture), 100% of those observed closed-candle decision outcomes appear with correct classification and a reason when rejected.
- **SC-005**: After a run with at least one simulated fill, 100% of fills appear in the inspectable trade list, and the summary shows distinguishable net P&L, total fees, total slippage, trade counts, win rate, maximum drawdown, best/worst trade, and buy-and-hold return.
- **SC-005a**: After backend restart, previously completed backtests within the retention limit remain inspectable (configuration, summary, trades, decisions). Creating an additional completed run beyond 20 removes the oldest completed run. Operator delete removes a chosen run.
- **SC-006**: When historical data for the requested window is missing or insufficient, 100% of observed attempts fail safely with a clear reason and 0 fabricated candles/prices used for fills.
- **SC-006a**: When a configured window exceeds the documented maximum load size, 100% of observed attempts are rejected before run with a clear oversized-history reason and 0 silent truncations.
- **SC-007**: Review confirms no private exchange trading API usage and no real order placement on the backtest path; XT-specific payloads do not appear in backtest domain contracts.
- **SC-008**: 100% of out-of-scope capabilities listed for this feature remain unimplemented in the Feature 004 deliverable.
- **SC-009**: On ~375px width, primary backtest configure/run/summary/trade-inspection affordances remain completable/readable without desktop-only controls.

## Assumptions

- Feature 002 normalized public Spot market data remains the sole market-data source for historical candles; Feature 004 may require date-range retrieval through that boundary but does not invent a second exchange integration.
- Feature 003 Dual EMA strategy, long-only full-position model, sizing formula, fee/slippage defaults, controller/risk authority, and Decimal money semantics are the semantic baseline for backtest trading behavior.
- Default fee and slippage when omitted match Feature 003: **0.10% fee** and **0.05% adverse slippage per fill side**.
- Profit-target and max-loss rates are **optional** for backtests; when set, they act as early-exit bounds using Feature 003 liquidation NET semantics; when unset, the run processes through the historical window (aside from other rejects and end-of-run flatten).
- Session “duration” as a live wall-clock bound is not a primary backtest input; the historical start/end window defines the evaluation period.
- Maximum trades (`max_trades`) is an **optional** backtest input; when set, enforce like Feature 003 (strategy fills only); when omitted, apply **no** max-trades cap.
- End-of-run open longs are always flattened once at the final processed closed candle’s **close** for determinate ending capital.
- Strategy fills use **next candle open** after the signal candle; missing N+1 means no normal strategy fill.
- Buy-and-hold comparison is cost-aware and aligned with next-open entry / final-close exit where a next candle exists (FR-017).
- Maximum drawdown is taken from the series of liquidation-consistent equity values recorded after **every processed closed candle**.
- Win/loss statistics are based on completed round-trips (FR-020).
- Backtesting lives under the Auto Trading primary area; no fourth primary nav item.
- A backtest run does not replace or resume a live simulation session and does not mutate simulation session balances.
- Oversized history windows are rejected before run against a documented max candle count / per-timeframe span; exact numeric caps are set in planning/docs, not by silent truncation.
- Completed backtests are persisted (configuration, summary, trades, decisions), survive backend restart, are operator-deletable, and retain at most **20** completed runs (evict oldest when exceeded).
- Local single-operator use; multi-user auth remains out of scope.
- Constitution Market Sentiment capabilities remain out of scope here.
- Real-money mode remains unavailable/non-functional.
