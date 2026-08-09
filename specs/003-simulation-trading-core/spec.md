# Feature Specification: Simulation Trading Core

**Feature Branch**: `003-simulation-trading-core`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Create Feature 003: Simulation Trading Core for CryptoAutoTrading — first end-to-end automated trading machine using simulated money only; consume Feature 002 normalized market data; strategy proposes, Trading Controller and Risk Manager decide; one active simulation session; journals; NET P&L; hard session stops; emergency stop; no real XT orders or credentials."

## Clarifications

### Session 2026-08-09

- Q: For Feature 003 simulation, which position model should BUY and SELL signals use? → A: Long-only with single full position: BUY only from flat; SELL only closes entire long; no partial adds
- Q: Which single baseline strategy should Feature 003 use for simulation signals? → A: Dual moving-average crossover on the session candle timeframe (fast MA crosses slow MA → BUY/SELL; otherwise HOLD)
- Q: When a hard stop ends a session that still holds a long position, what should happen to that simulated position? → A: Force one simulated full close (SELL) at the latest safe market price with documented fees/slippage and journal the trade, if a safe price exists; if no safe price exists, do not invent a close—stop the session, leave the position unresolved for execution, and fail safe
- Q: When should the dual moving-average strategy evaluate and emit a new BUY, SELL, or HOLD signal during an active session? → A: Evaluate only on each new closed candle for the session timeframe
- Q: What default simulated fee and slippage assumptions should Feature 003 apply when the operator does not override costs? → A: Documented non-zero defaults, overridable per session: 0.10% fee + 0.05% adverse slippage per side

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure and start one simulation session (Priority: P1)

A developer or operator opens Auto Trading, configures a single simulated trading session (pair, starting capital, allocated capital, strategy, timeframe, duration, target net profit **rate**, maximum loss **rate**, max trades, max position size), starts it, and clearly sees that the session is simulation-only (not real money). Profit/loss inputs are percentages of allocated capital; the UI shows both each rate and its derived currency amount.

**Why this priority**: Without a bounded, startable simulation session, there is no controlled trading machine to run.

**Independent Test**: Configure required session bounds for a supported pair, start the session, confirm it is active and unmistakably labeled as simulation, with real-money mode unavailable.

**Acceptance Scenarios**:

1. **Given** the application is running locally without exchange trading credentials, **When** the user configures a simulation session with all required bounds and starts it, **Then** exactly one active simulation session runs and is visually unmistakable from real-money mode.
2. **Given** a simulation session is already active, **When** the user attempts to start another, **Then** the system refuses a second concurrent session and keeps the existing session as the only active one.
3. **Given** required configuration is incomplete or invalid, **When** the user attempts to start, **Then** the system blocks start with a clear reason and does not begin trading activity.
4. **Given** the product UI, **When** the user looks for real-money trading controls, **Then** real-money mode remains unavailable/non-functional for this feature.

---

### User Story 2 - Run the controlled pipeline from market data to simulated execution (Priority: P1)

While a session is active, the system consumes public market data for the session pair, runs one baseline strategy that emits BUY, SELL, or HOLD, and routes every non-HOLD signal through the Trading Controller and Risk Manager before any simulated execution. Approved signals become simulated trades; rejected signals do not change balances or positions.

**Why this priority**: This is the constitutional trading machine: strategy proposes; control and risk decide.

**Independent Test**: With an active session and safe market data, observe at least one non-HOLD path that is either approved into a simulated trade or rejected with an explicit reason—never a direct strategy-to-balance update.

**Acceptance Scenarios**:

1. **Given** an active simulation session and safe market data, **When** the strategy emits HOLD, **Then** no simulated trade executes and no balance/position change occurs from that signal.
2. **Given** an active session and a non-HOLD signal that is valid for the long-only full-position model, **When** control and risk approve it, **Then** a simulated trade executes using market prices from the existing normalized market-data layer (no private exchange trading APIs): BUY opens a full long from flat, or SELL fully closes the long.
2a. **Given** an active session, **When** the current candle for the session timeframe is still forming, **Then** the strategy does not emit a new trading signal from that incomplete candle or from intrabar quote ticks alone.
3. **Given** a non-HOLD signal, **When** control or risk rejects it (e.g., max trades, insufficient balance, stale data, emergency stop), **Then** balances and positions remain unchanged by that signal and the rejection reason is recorded.
4. **Given** any strategy output, **When** processing completes, **Then** the strategy never bypasses the Trading Controller and Risk Manager to modify simulated funds or positions.

---

### User Story 3 - Observe journals, balances, and NET session P&L (Priority: P1)

The user can inspect simulated balance and position, gross and net P&L (with costs distinguished), trade count, Decision Journal (including rejections), and Trade Journal for executed simulated trades.

**Why this priority**: Traceability and NET P&L are required for trust, audit, and correct hard-limit evaluation.

**Independent Test**: After activity that includes at least one approval and one rejection (or forced rejection), open journals and P&L views and confirm records and NET accounting are present and consistent.

**Acceptance Scenarios**:

1. **Given** strategy decisions have occurred, **When** the user opens the Decision Journal, **Then** each material decision is listed, including rejected non-HOLD signals with reasons.
2. **Given** at least one simulated trade has executed, **When** the user opens the Trade Journal, **Then** each executed simulated trade is listed with enough detail to understand pair, side, size, prices/costs context, and timing.
3. **Given** an active or recently active session, **When** the user views session economics, **Then** they can see gross P&L, fees, slippage/execution costs, and net P&L as distinct concepts, plus trade count and current simulated balance/position.
4. **Given** Portfolio is not yet a full portfolio product, **When** the user views Portfolio (if anything is shown), **Then** only simulation state needed to understand the active/recent session may appear—not a full portfolio-management experience.

---

### User Story 4 - Hard stops, manual stop, and emergency stop (Priority: P1)

The session stops automatically when a hard limit is hit (profit target, max loss, max trades, duration, emergency stop, or unrecoverable unsafe market data). The user can also stop manually or activate emergency stop. After a hard control stop, new signals do not execute in that session.

**Why this priority**: Capital protection and session bounds are non-negotiable; stop authority must be enforceable.

**Independent Test**: Configure a tight, testable hard limit (or trigger emergency stop), run until it fires, confirm session stops and further signals do not execute.

**Acceptance Scenarios**:

1. **Given** an active session whose liquidation-based Session NET P&L reaches the derived target net profit amount (from allocated capital × configured rate), **When** the system evaluates bounds, **Then** the session stops automatically and further new signals do not execute in that session.
2. **Given** liquidation-based Session NET P&L reaches the derived maximum session loss amount (from allocated capital × configured rate), **When** the system evaluates bounds, **Then** the session stops automatically and further new signals do not execute.
3. **Given** maximum trades or session duration is reached, **When** the bound is hit, **Then** the session stops automatically under the same no-new-execution rule.
4. **Given** an active session, **When** the user activates emergency stop, **Then** new trading activity for that session halts immediately under operator control.
5. **Given** an active session, **When** the user stops the session manually, **Then** the session ends without requiring emergency stop, and new signals do not execute afterward.
6. **Given** market data required for decisions is stale, malformed, missing, or otherwise unsafe, **When** a trading decision would otherwise proceed, **Then** the system rejects/suspends execution rather than guessing; if the state is unrecoverable per session rules, the session stops.
7. **Given** a hard stop fires while a long is open and a safe market price is available, **When** the session terminates, **Then** the system performs one forced simulated full close, journals it, and stops further signal execution.
8. **Given** a hard stop fires while a long is open and no safe market price is available, **When** the session terminates, **Then** the system does not invent an exit price, stops further signal execution, and leaves the unsafely-unflattened state inspectable.

---

### User Story 5 - Monitor simulation from Auto Trading on phone and desktop (Priority: P2)

On Auto Trading (and any minimal session summary allowed elsewhere), the user can configure/monitor the simulation session on phone-width and desktop-width viewports without desktop-only gestures for primary session controls and status.

**Why this priority**: Operators must be able to supervise the machine on a phone; secondary to core pipeline correctness.

**Independent Test**: At ~375px width, start or view session status, stop or emergency stop affordances, and key status/P&L/journal entry points remain usable.

**Acceptance Scenarios**:

1. **Given** a phone-width viewport, **When** the user works with Auto Trading simulation controls/status, **Then** configure/start/inspect/stop/emergency-stop and core status remain readable and usable.

---

### Edge Cases

- Strategy emits BUY while already long → reject as conflicting position state (Feature 003 allows only flat → full long via BUY; no adds); journal the decision.
- Strategy emits SELL while flat (no long) → reject as conflicting position state; journal the decision.
- Strategy emits SELL while long → only a full close of the entire long is allowed (no partial reduce).
- Insufficient simulated balance for the proposed full BUY size → reject; no partial silent oversize.
- Full BUY would exceed `allocated_capital` or `max_position_size` → reject (sizing uses the min with affordable cash).
- Position-size limit would be exceeded by a full BUY → reject.
- Market data becomes stale mid-session → reject/suspend new execution; do not trade on guessed prices.
- Incomplete (still-forming) candle or quote tick alone → no new strategy signal; wait for the session-timeframe candle to close.
- Hard limit and a new signal arrive near the same time → hard stop wins; no new execution after stop.
- User spams start/stop/emergency stop → system remains consistent; at most one active session; emergency stop remains decisive.
- Fees/slippage configuration missing → apply initial documented defaults: **0.10% fee** and **0.05% adverse slippage per side**; never pretend costs are zero unless the operator explicitly overrides to zero.
- Session ends with an open simulated position under a hard stop → if a safe price exists, force one simulated full close and journal it; if not, do not invent a close; stop new execution and keep the unsafe-unflattened state inspectable; never send a real exchange order.
- Feature 002 market-data failure while session active → fail safe; do not fabricate prices to keep trading.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a simulation trading mode that never places real exchange orders and never requires exchange trading credentials.
- **FR-002**: The system MUST consume the existing normalized public market-data layer (Feature 002) for session pricing and strategy inputs; it MUST NOT call private/authenticated exchange trading APIs.
- **FR-003**: The system MUST enforce the pipeline: Market Data → Strategy Engine → Trading Signal → Trading Controller → Risk Manager → Simulation Execution → Simulated Position/Balance → Session P&L → Continue or Stop. Strategies MUST NOT modify balances or positions directly.
- **FR-004**: The system MUST allow at most one active simulated trading session at a time.
- **FR-005**: A simulation session MUST be configurable with: trading pair, starting simulated capital, **allocated session capital**, one baseline strategy, strategy signal timeframe, session duration, **target net profit rate** (percent/fraction of allocated capital), **maximum session loss rate** (percent/fraction of allocated capital), maximum number of trades, and maximum position size. Sessions MUST NOT start without these bounds defined. The system MUST derive and persist absolute threshold amounts (`allocated_capital × rate`) for auditability. Simulated fee and slippage rates MUST be overridable per session; when omitted, FR-012a defaults apply. Auto Trading MUST display both the configured percentage and the resulting currency amount for profit target and max loss.
- **FR-005a**: Full-position BUY sizing MUST use  
  `intended_notional = min(current_cash / (1 + fee_rate), allocated_capital, max_position_size)`.  
  The simulation MUST NOT deploy more than `allocated_capital` even when `starting_capital` or current cash is larger.
- **FR-006**: The feature MUST use exactly one baseline strategy: a **dual EMA crossover** with **EMA(9)** fast and **EMA(21)** slow on closed candle **close** prices for the session’s strategy signal timeframe. A deterministic cross produces BUY or SELL; otherwise HOLD. No other strategies are in scope for Feature 003.
- **FR-006a**: The strategy MUST evaluate and emit a new signal **only when a candle for the session timeframe closes**. It MUST NOT emit trading signals from intrabar quote ticks or from still-forming (incomplete) candles. Between closed-candle evaluations, the prior signal does not re-trigger execution by itself.
- **FR-007**: The strategy MUST be able to emit BUY, SELL, and HOLD signals only for this feature’s signal vocabulary.
- **FR-007a**: Feature 003 MUST use a **long-only single full-position** model: the simulated account is either **flat** or holding **one full long** for the session pair. BUY is valid only from flat and opens the entire allowed long in one fill (subject to FR-005a sizing). SELL is valid only while long and closes the **entire** long in one fill. Partial adds, partial reduces, pyramiding, and short selling MUST NOT be supported. Invalid BUY/SELL relative to position state MUST be rejected as conflicting position state and journaled.
- **FR-008**: Every non-HOLD signal MUST pass through the Trading Controller and Risk Manager before simulated execution. HOLD MUST NOT execute a trade.
- **FR-009**: The Trading Controller and Risk Manager MUST be able to reject signals for explicit reasons including at least: session not active; profit target already reached; maximum loss already reached; maximum trades reached; insufficient simulated balance; allocated-capital or position-size limit binding; invalid or stale market data; conflicting position state; emergency stop active; and other explicit control/risk rules introduced by this feature.
- **FR-010**: Every material strategy decision MUST create a Decision Journal record, including rejected non-HOLD signals and their rejection reasons.
- **FR-011**: Every executed simulated trade MUST create a Trade Journal record.
- **FR-012**: Simulated execution MUST use market prices from the normalized market-data layer, apply configurable simulated trading fees, apply a simple documented slippage assumption, update simulated balances and positions deterministically, and compute realized and unrealized P&L.
- **FR-012a**: Unless the operator overrides them for the session, Feature 003 MUST apply these **initial documented defaults per fill side**: trading fee **0.10%** of notional and **0.05% adverse slippage** (BUY fills worse/higher; SELL fills worse/lower). Defaults MUST be visible in product/docs; zero-cost simulation MUST NOT be the silent default.
- **FR-013**: The system MUST distinguish gross P&L, fees, slippage/execution costs, and net P&L in session economics.
- **FR-014**: Session profit-target and maximum-loss thresholds MUST be evaluated using **Session NET P&L** under this precise rule: while the session is **flat**, Session NET P&L equals simulated cash minus session start equity; while **long** with a **safe** market price, Session NET P&L equals **liquidation equity** minus start equity, where liquidation equity is cash plus the net proceeds of a **hypothetical** full adverse SELL at that safe price using the session’s fee and slippage assumptions (not raw mark-to-market equity). That Session NET P&L MUST be compared to the **derived absolute** profit-target and max-loss amounts from FR-005 (`allocated_capital × configured rates`). Gross price movement alone and raw mark equity MUST NOT be used as the hard-limit metric. Raw mark-to-market equity and unrealized gross P&L MAY be displayed for information. Hypothetical exit costs used for threshold evaluation MUST NOT be ledgered separately from an actual forced close that applies those costs once.
- **FR-014a**: `max_trades` MUST limit normal **strategy-driven** simulated fills only. If that limit is reached while long, the system MUST still allow **one** forced safety close required to terminate, even if `trade_count` becomes `max_trades + 1`. That forced close MUST be Trade-Journaled with an explicit forced-close marker and MUST NOT enable further strategy execution.
- **FR-015**: The session MUST automatically stop when any hard termination condition occurs: target net profit reached; maximum session loss reached; maximum trades reached; session duration expires; emergency stop activated; or unrecoverable unsafe market-data state per session rules.
- **FR-015a**: If a hard stop (including emergency stop and automatic hard limits) ends a session while a long position is open, and a **safe** market price is available, the system MUST execute one forced simulated full close (SELL of the entire long) at that price using documented fees/slippage, create a Trade Journal record, then complete the stop. If no safe price is available, the system MUST NOT invent a close price: it MUST still stop new signal execution, fail safe, and leave the position marked as not safely flattened (inspectable), without fabricating P&L from a guessed exit.
- **FR-016**: When a session is stopped by a hard control condition (or manual/emergency stop), new strategy signals MUST NOT execute within that session.
- **FR-017**: Users MUST be able to create/configure a simulation session, start it, inspect current state, stop it manually, activate an emergency stop, and inspect simulated balance/position, gross/net P&L, trade count, Decision Journal, and Trade Journal.
- **FR-018**: Auto Trading MUST be extended enough to configure and monitor the simulated session for this feature.
- **FR-019**: Portfolio MUST NOT become a full portfolio-management feature in this scope; only simulation state required to understand the active/recent session MAY be exposed there.
- **FR-020**: Simulation mode MUST be visually unmistakable from real-money mode. Real-money mode MUST remain unavailable/non-functional in this feature.
- **FR-021**: When required market data is stale, malformed, missing, or otherwise unsafe for a trading decision, the system MUST reject or suspend execution rather than guess or fabricate prices.
- **FR-022**: Completing this feature MUST NOT introduce: authenticated/private exchange trading APIs; real order placement; real-money trading; futures; margin; leverage; multiple simultaneous sessions; multiple strategies; strategy optimization; machine learning; AI prediction; sentiment-driven trading; news-driven trading; backtesting; production deployment; Google authentication; or multi-user functionality.

### Key Entities

- **Simulation Session**: One bounded simulated trading run with pair, capital, strategy, timeframe, duration, and hard limits; at most one active at a time.
- **Strategy Signal**: BUY, SELL, or HOLD proposal from the dual moving-average crossover baseline, produced only on closed candles for the session timeframe; advisory only.
- **Control/Risk Decision**: Approve or reject outcome for a non-HOLD signal, with explicit reason when rejected.
- **Simulated Trade**: Deterministic simulated fill using public market prices plus documented fee and slippage assumptions; never a real exchange order.
- **Simulated Balance / Position**: Session cash and open position state updated only by approved simulated execution (and mark-to-market for unrealized P&L). Position state is long-only: flat or one full long; no partial size changes and no shorts.
- **Session Economics**: Gross P&L, fees, slippage/execution costs, informational mark equity/unrealized, liquidation equity, hard-limit Session NET P&L, trade count / strategy fill count.
- **Decision Journal Entry**: Trace record of a material strategy decision, including rejections.
- **Trade Journal Entry**: Trace record of an executed simulated trade.
- **Emergency Stop**: Operator control that immediately halts new trading activity for the session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer following project docs can start the app locally and create/start a simulation session for a supported pair in under 20 minutes (tools already installed), with no exchange trading credentials.
- **SC-002**: In a successful demo path, at least one non-HOLD signal is processed through control/risk such that the outcome is either an approved simulated trade or an explicit rejection—never a silent strategy-to-balance write—observable within one local session run.
- **SC-003**: After a run that includes at least one rejection, 100% of observed rejected non-HOLD signals appear in the Decision Journal with a reason.
- **SC-004**: After a run that includes at least one simulated fill, 100% of those fills appear in the Trade Journal, and session economics show gross P&L, fees, slippage/execution costs, and net P&L as distinguishable values.
- **SC-005**: When a configured hard limit is reached under the Session NET P&L / trades / duration / emergency / unsafe-data rules, the session stops and 0 further new simulated executions occur in that session afterward in the observed test window.
- **SC-006**: In forced unsafe market-data conditions, 100% of observed trading-decision attempts fail safe (reject/suspend) with 0 fabricated prices used for execution.
- **SC-007**: Review confirms no private exchange trading API usage and no real order placement path in this feature’s deliverable; real-money mode remains non-functional; simulation labeling is visible wherever session trading status is shown.
- **SC-008**: 100% of out-of-scope capabilities listed in this specification remain unimplemented in this feature’s deliverable.
- **SC-009**: On ~375px width, primary Auto Trading simulation configure/start/status/stop/emergency-stop affordances remain completable/readable without desktop-only controls.

## Assumptions

- Feature 002 normalized public Spot market data (USDT pairs, quotes, history, freshness/STALE rules) remains the market-data source for simulation decisions.
- Feature 001 shell (three primary areas, routing, health) remains the host application; Auto Trading is the primary surface for simulation control; Dashboard market viewing may continue to exist independently.
- The sole baseline strategy is a dual moving-average crossover on the session candle timeframe (clarified 2026-08-09); concrete periods are **EMA(9)/EMA(21)** on closed candle closes (locked in plan/research 2026-08-09).
- Strategy evaluation runs only on each newly **closed** candle for the session timeframe; the same candle `openTime` MUST NOT be processed twice (clarified + plan 2026-08-09).
- Position model is long-only single full position (BUY only from flat; SELL only full close); clarified 2026-08-09. Full BUY notional is `min(current_cash/(1+fee_rate), allocated_capital, max_position_size)` (plan update 2026-08-09).
- Simulated fees and slippage use documented non-zero defaults of **0.10% fee** and **0.05% adverse slippage per fill side**, overridable per session (clarified 2026-08-09). Zero-cost simulation is not the silent default.
- “Safe” market data for trading decisions means Feature 002 quote freshness: prefer `observedAt` else `retrievedAt`, **60-second** threshold, valid payload (plan).
- Starting simulated capital sets initial cash; **allocated capital** is a distinct enforceable deploy bound. UI MAY default allocated equal to starting when a single capital figure is entered, but both remain represented.
- Profit target and max loss are configured as **rates of allocated capital**; derived absolute USDT amounts are stored and shown beside the percentages in the UI (plan update 2026-08-09).
- Mark-to-market equity and unrealized gross MAY be displayed; profit target / max loss use **liquidation** Session NET compared to those derived absolute amounts. Hypothetical evaluation costs are not double-counted with the actual forced close (plan update 2026-08-09).
- `max_trades` caps strategy-driven fills; one forced safety close may make `trade_count = max_trades + 1` (plan update 2026-08-09).
- On hard stop with an open long: forced simulated full close if a safe price exists; otherwise fail-safe stop without inventing an exit (clarified 2026-08-09).
- Session states: `CONFIGURED` → `RUNNING` → `STOPPING` → `STOPPED`. Backend restart forces `STOPPED` with `backend_restart` and does not resume or auto-flatten (plan).
- Journals are inspectable in-product for local single-operator use; multi-user auth is out of scope.
- Persistence: **SQLite** for sessions and Decision/Trade journals (plan); Feature 002 UI prefs remain `localStorage`.
- Real-money mode is rejected at the API/session boundary; Feature 003 does not ship a real XT execution implementation (plan update 2026-08-09).
- Constitution Market Sentiment Dashboard capability remains out of scope here (no sentiment-driven trading, no Fear & Greed trading inputs).
- Real-money mode exists only as an unavailable/non-functional distinction to keep simulation unmistakable; no real-money session can be started in this feature.
