# Feature Specification: Stage-1 Trading Gap-Close

**Feature Branch**: `025-stage1-trading-gap-close`

**Created**: 2026-08-16

**Status**: Draft

**Input**: Feature 025 — Close only the concrete Stage-1 gaps required for a trustworthy Simulation Trading MVP before Feature 015 Controlled Real. Bounded gap-close (not infrastructure): basic per-position fixed TP/SL in Simulation and Backtest (closed-candle OK; no ticks/trailing/multi-level); document intentional Simulation vs Backtest fill differences and fix only accidental semantic inconsistencies; add ~3–4 diverse conventional strategy/signal primitives for later Torque/GE; minimal operator UI for entry/position/TP/SL/exit reason; repeated entry/exit cycles with correct cash/holdings/P&L. Out of scope: Real XT placement, RealExecutionAdapter activation, Real mode, Torque, GE, 014 recovery expansion, Portfolio redesign, ticks/WebSockets, advanced analytics, plugin architecture, shorts, multi-symbol Real, VPS/cloud.

## Clarifications

### Session 2026-08-16

- Q1: Closed-candle TP/SL trigger basis? → **B**: High→TP, Low→SL on the closed bar. Only **post-entry** price movement may trigger. If both touched and intra-bar order is unknowable, **SL wins**. Trigger detection MUST NOT invent the Execution fill price.
- Q2: Strategy candle input for new primitives? → **A**: Minimally enrich strategy candle input with **OHLC**. Volume remains optional and a volume-based strategy is included **only** when XT volume is confirmed reliable for both Backtest and Simulation; otherwise defer volume strategy.
- Q3: TP/SL configuration shape? → **A**: Operator configures **percentage only**. Persist and display **derived absolute levels** based on the **actual entry fill price**.
- Q4: Protective exit fill price when TP/SL triggers? → **B**: TP/SL decide that an exit is required, not the fill price. Preserve each mode’s existing execution semantics — Backtest next-open model; Simulation trustworthy live mark. Do **not** invent a fill at the TP/SL trigger level.
- Q5: Evaluate TP/SL on the entry-fill candle? → **A**: Never. Protective TP/SL evaluation begins with the **next** processed closed candle after the position opens.
- Q6: Mid-position TP/SL changes while long? → **A**: No. Percentages and derived absolute levels are fixed when the position opens from effective run configuration and stay unchanged until that position closes. Dynamic/manual stop management is out of scope for Feature 025.
- Q7 (analyze remediation): Do protective TP/SL exits count toward `maxTrades`? → **No**. Use forced/safety close path; do not increment `strategyFillCount`; keep reasons `take_profit` / `stop_loss`.

## Behavior locks (non-negotiable)

1. **Single pipeline** — Market Data → Strategy → Controller → Risk → Execution → Portfolio/Accounting → journals. TP/SL MUST NOT bypass Controller, Risk, or Execution.
2. **Never invent** prices, fills, decisions, or balances. TP/SL **trigger ≠ fill price**.
3. **Long-only** current architecture preserved (one position per session).
4. **Closed-candle** evaluation for strategy signals and for MVP TP/SL (no tick/intrabar/WebSocket work).
5. **TP/SL trigger basis (locked)**: on each processed closed candle while long, **high** may trigger take-profit and **low** may trigger stop-loss; **never** on the entry-fill candle — evaluation starts on the next processed closed candle; if both touch with unknowable order, **SL wins**.
6. **TP/SL config (locked)**: operator enters **percentages only**; absolute levels are derived from actual entry fill price and shown/persisted for the open position; **no mid-position TP/SL changes** while long (dynamic/manual stop management out of scope).
7. **Protective exit fills (locked)**: TP/SL trigger detection does **not** set fill price; Execution uses each mode’s existing semantics (Backtest next-open; Simulation trustworthy live mark). Never invent a fill at the TP/SL level.
8. **Strategy candles (locked)**: Feature 025 minimally enriches strategy input with **OHLC**; volume strategy deferred unless reliability gate passes.
9. **Simulation ≠ Backtest fill price selection may differ intentionally**; do not force identical mark models. Fix only accidental semantic inconsistencies in strategy/risk/TP/SL/accounting.
10. **Feature 014 recovery frozen** — reuse as-is unless a concrete defect is found during validation.
11. **No Real trading** — Feature 015 owns Controlled Real.
12. **No Torque / GE** in this feature.

## Repository baseline (authoritative today)

- **Per-position TP/SL**: not implemented. Session-level profit target / max loss and emergency/forced flatten exist.
- **Strategy exit**: long-only full SELL via strategies; Risk/Execution apply fills.
- **Strategies (close-only input today)**: `dual_ema`, `rsi`, `macd`, `bollinger_bands`, `breakout`. Strategy contract evaluates `Sequence[CandleClose]` (open time + close only) — Feature 025 enriches to OHLC for strategies that need range.
- **Simulation fills**: live mark / last-price style for approved intents on closed candles.
- **Backtest fills**: historical next-open style for strategy fills (Feature 004).
- **Fees/slippage**: applied on fill economics in both modes.
- **XT candle volume**: present on market-data models (`volumeBase` / `volumeQuote`); strategies do not consume volume or high/low today.
- **Portfolio**: Feature 009 funding/holdings/allocations exist; freeze allocation expansion; no Portfolio redesign in 025.

## TP/SL semantics (locked)

### Configuration

- Operator configures per-position take profit and/or stop loss as fixed **percentages of entry only** (MVP). Absolute prices are **not** operator-edited.
- Either side MAY be omitted/disabled independently.
- After a successful BUY fill, the system **derives and persists** absolute TP and/or SL prices from the **actual entry fill price** and the configured percentages, and **displays** those levels while the position is open.
- While that long remains open, the operator MUST NOT change TP/SL percentages or derived absolute levels for that position. Dynamic/manual stop management is out of scope for Feature 025. New percentages apply only to a later position via the effective run configuration after the current position is flat.
- Session profit target / max loss / max trades / duration / emergency stop remain in force and are independent of per-position TP/SL.
- Defaults: TP/SL **disabled** unless the operator (or copied operator defaults) sets percentages. Feature 008 may gain optional default percentage fields without redesigning Settings architecture.

### When levels are calculated

- Absolute TP/SL levels are established when a **long position opens** (successful BUY fill), from the **actual entry fill price** produced by Execution (not a second invented price).
- Levels remain fixed for the life of that position (no trailing; no re-anchor on marks; no mid-position operator edits).
- When the position closes (any exit), active TP/SL levels clear until the next entry.

### Fees / slippage vs trigger levels

- Stored TP/SL **trigger levels do not include fees or slippage**.
- Fees/slippage apply only when Execution produces the exit fill economics (same as existing exits).

### Closed-candle trigger evaluation

- TP/SL are evaluated on each newly processed **closed** candle while a long is open, through the normal session/backtest processing loop.
- **Take profit** may trigger when the closed candle’s **high** reaches or exceeds the TP level.
- **Stop loss** may trigger when the closed candle’s **low** reaches or is at/below the SL level.
- Protective TP/SL MUST **not** be evaluated on the **entry-fill candle**. Evaluation begins with the **next** processed closed candle after the position opens (post-entry only; no use of that entry bar’s high/low for triggers).
- Detecting a trigger MUST NOT invent the Execution fill price. After Controller/Risk approve the protective exit intent, **fill price follows each mode’s existing Execution model**: Backtest uses its **next-open** semantics (when a next candle exists; otherwise fail closed / end-of-series rules already defined for Backtest); Simulation uses a **trustworthy live mark**. Filling at the TP or SL trigger level is forbidden.
- Triggers produce an exit **intent** that still passes Controller → Risk → Execution (protective exit path — not a strategy bypass).

### Precedence on the same processed candle

When multiple exit conditions are true on the same processed candle (and mode still allows trading/exits):

1. **Emergency / operator stop / session hard-stop** (profit target, max loss, duration, max trades, portfolio max-loss as already defined) take precedence and end or flatten per existing rules.
2. Else **Stop Loss** before **Take Profit** (capital protection).
3. Else **strategy EXIT (SELL)** if issued for that candle.
4. Protective TP/SL exits MUST NOT wait for strategy agreement.

If both TP and SL are touched on the same closed candle and intra-bar order is unknowable, **SL wins**.

### Forced / emergency / session exits vs TP/SL

- Session/emergency/forced flatten remains authoritative and may close the position even when TP/SL are set.
- Protective TP/SL exits themselves use the **forced/safety close path** for fill accounting flags so they do not consume `maxTrades` / `strategyFillCount`, while still recording `take_profit` / `stop_loss` reasons.
- Exit reason recorded for the operator MUST distinguish: `take_profit`, `stop_loss`, `strategy_exit` (or existing strategy/risk reason codes), and existing session/emergency/forced stop reasons — without inventing fills.

### Persistence / history / results

- Configured **percentages** (and whether each side is enabled) MUST be part of the effective run configuration for Simulation and Backtest.
- While a position is open, operator-visible state MUST include entry fill price and **derived absolute** TP/SL levels.
- When a position closes via TP/SL, history/results/journals MUST make the exit reason understandable (including after session stop).

### Simulation and Backtest consistency

- TP/SL **rules** (config, level derivation, high/low triggers, precedence, accounting outcomes) MUST be consistent across Simulation and Backtest.
- **Fill price selection** for entries/exits may still follow each mode’s intentional model (Simulation live mark vs Backtest next-open / historical references), including protective TP/SL exits. That difference MUST be documented, not “fixed away.” Filling at the TP/SL trigger level is not an allowed “intentional difference.”

## Additional strategy set (locked direction)

Existing coverage: Dual EMA (trend), MACD (trend/momentum), RSI (momentum / mean-reversion oscillator on close), Bollinger (volatility bands / mean-reversion on close), Breakout (lookback close extremes).

Feature 025 **minimally enriches** strategy candle input with **OHLC** so range-based primitives are honest. Volume fields may be passed through when present but a **volume-based strategy is deferred** unless reliability for both Backtest and Simulation is confirmed during plan/research.

**Target additions (bounded; finalize exact IDs/parameters in plan without expanding to a TA library):**

| Addition | Diversity role |
|----------|----------------|
| **Stochastic** | Momentum oscillator ≠ RSI (uses high/low range) |
| **Keltner / ATR channel** | Volatility channel ≠ Bollinger |
| **Rate of Change / Momentum** | Close-based momentum ≠ Dual EMA/MACD |
| **Relative volume** (optional 4th) | Only if volume reliability gate passes; otherwise omit |

Do **not** add MA-variant clutter, plugin infrastructure, ensembles, Torque, or GE.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Attach TP/SL and exit by protective levels (Priority: P1)

As an operator, I want to configure fixed per-position take profit and stop loss so an open long can exit through the normal pipeline when those levels are hit on closed-candle evaluation—in both Backtest and Simulation.

**Why this priority**: Missing per-position TP/SL is the primary Stage-1 gap before Controlled Real; session stops alone are not enough for the product risk model.

**Independent Test**: Configure TP and/or SL; open a long; feed/process candles that cross the level; assert exit via Execution, correct cash/holdings/P&L, and exit reason TP or SL—in Backtest and Simulation.

**Acceptance Scenarios**:

1. **Given** a long is opened with TP configured, **When** a later closed candle (not the entry-fill candle) satisfies the TP trigger rule, **Then** the position closes through Controller → Risk → Execution with exit reason take-profit and no invented price at the TP level.
2. **Given** a long is opened with SL configured, **When** a later closed candle satisfies the SL trigger rule, **Then** the position closes through the same pipeline with exit reason stop-loss.
3. **Given** TP/SL are omitted/disabled, **When** a long is open, **Then** no protective TP/SL exit is generated from those levels (strategy and session stops still apply).
4. **Given** the same TP/SL configuration, **When** the scenario is run in Backtest and in Simulation, **Then** TP/SL decision rules and accounting outcomes are consistent aside from intentional fill-price-model differences.

---

### User Story 2 - Strategy exit still works with TP/SL present (Priority: P1)

As an operator, I want strategy SELL exits to remain available and correctly ordered relative to TP/SL so protective exits are never blocked by waiting for strategy agreement.

**Why this priority**: Audit requires strategy exit independent of TP/SL, with clear precedence.

**Independent Test**: Open long with TP/SL set; produce strategy SELL before levels hit; also construct same-candle conflicts; assert precedence and single exit fill.

**Acceptance Scenarios**:

1. **Given** a long with TP/SL configured but levels not yet triggered, **When** the strategy emits SELL on a closed candle, **Then** the position can close via strategy exit through the pipeline.
2. **Given** SL and strategy SELL both apply on the same processed candle, **When** exits are evaluated, **Then** stop-loss takes precedence over strategy exit and only one closing fill occurs.
3. **Given** TP and SL both would trigger on the same processed candle, **When** exits are evaluated, **Then** stop-loss wins.
4. **Given** repeated BUY → exit (TP or SL or strategy) → BUY cycles, **When** accounting is inspected, **Then** cash, holdings, and P&L remain correct after each cycle.

---

### User Story 3 - Understand intentional Simulation vs Backtest differences (Priority: P1)

As an operator, I want intentional Simulation vs Backtest execution/fill differences documented and accidental semantic inconsistencies fixed so I can trust Backtest → Simulation comparison for Stage-1.

**Why this priority**: Operators must not treat unexplained result gaps as random bugs.

**Independent Test**: Review documented difference list; run a shared configuration; confirm differences match documentation; verify TP/SL/strategy/risk/accounting semantics are not accidentally divergent.

**Acceptance Scenarios**:

1. **Given** Feature 025 documentation, **When** an operator compares Simulation and Backtest for the same strategy/config, **Then** intentional fill/price-selection differences are stated explicitly.
2. **Given** an accidental inconsistency in strategy/risk/TP/SL/accounting semantics between modes, **When** Feature 025 is complete, **Then** that inconsistency is corrected (without redesigning Backtest’s intentional next-open model).

---

### User Story 4 - Bounded extra strategy primitives (Priority: P2)

As an operator/researcher, I want a small set of additional standard strategies so later Torque/GE has more diverse primitives—without a TA library project.

**Why this priority**: Diversity is required before Torque, but must stay bounded inside this gap-close.

**Independent Test**: List registered strategies; run each new strategy in Backtest (and Simulation where applicable); assert deterministic BUY/SELL/HOLD under fixtures.

**Acceptance Scenarios**:

1. **Given** the locked additional strategy set, **When** each new strategy is registered, **Then** it follows the existing Strategy → Controller → Risk → Execution path with validated parameters.
2. **Given** XT volume is not proven reliable for both modes, **When** Feature 025 ships, **Then** no volume-based strategy is locked in as required.
3. **Given** the new strategies, **When** an operator selects them like existing ones, **Then** Backtest and Simulation can run them without a plugin framework.

---

### User Story 5 - See entry, TP/SL, and exit reason in the UI (Priority: P2)

As an operator, I want minimal UI showing entry, position, TP level, SL level, and exit reason when closed—usable around ~375px—without a Portfolio redesign.

**Why this priority**: TP/SL are not operable if invisible; UI must stay minimal.

**Independent Test**: Open a Simulation with TP/SL; verify levels visible; after TP/SL/strategy exit, verify exit reason visible; check ~375px layout smoke.

**Acceptance Scenarios**:

1. **Given** an open long with TP/SL set, **When** the operator views the active session UI, **Then** entry and TP/SL levels are visible.
2. **Given** a position closed by TP, SL, or strategy exit, **When** the operator inspects session/history detail, **Then** the exit reason is understandable.
3. **Given** a ~375px viewport, **When** viewing the active session controls/status, **Then** TP/SL and exit information remain usable without adding a fourth primary nav or heavy charts.

---

### Edge Cases

- Only TP set, or only SL set.
- TP/SL disabled after defaults exist.
- Attempt to change TP/SL while long — rejected / not offered (MVP).
- Invalid TP/SL config (e.g., non-positive percent, SL on wrong side of entry for long) — must reject at configuration/start, fail closed.
- Same candle triggers SL and TP.
- Same candle triggers protective exit and strategy SELL.
- Entry-fill candle high/low must not trigger TP/SL; first eligible bar is the next processed closed candle.
- Session max-loss / profit-target / emergency stop while TP/SL active.
- Unsafe/missing mark during protective exit attempt — fail closed; do not invent exit price (align with existing unsafe flatten rules); never fill at TP/SL trigger level.
- Flat session: TP/SL levels not active.
- Backtest end-of-series flatten vs TP/SL on last bars (next-open unavailable → existing Backtest fail-closed/end rules).
- Repeated entry/exit cycles and journal/history readability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Feature 025 MUST remain a Stage-1 gap-close on the existing Simulation and Backtest paths only; it MUST NOT introduce a second trading engine, Real trading mode, Torque, or GE.
- **FR-002**: The system MUST support optional per-position fixed take-profit and stop-loss for long positions in Simulation and Backtest.
- **FR-003**: TP/SL exits MUST flow through Controller → Risk → Execution → Portfolio/Accounting and MUST NOT bypass Risk or invent fills/prices.
- **FR-004**: Operator-configured TP/SL MUST be **percentages only**. Absolute TP/SL levels MUST be derived from the **actual entry fill price** at position open, persisted for the open position, and displayed to the operator. Fees/slippage MUST NOT alter stored trigger levels. While a long is open, TP/SL percentages and derived absolute levels MUST NOT be changed for that position.
- **FR-005**: TP/SL evaluation MUST use closed-candle semantics only: **high ≥ TP** may trigger take-profit; **low ≤ SL** may trigger stop-loss; no tick/intrabar infrastructure in this feature. TP/SL MUST NOT be evaluated on the entry-fill candle; evaluation begins on the next processed closed candle after entry. Trigger detection MUST NOT invent the Execution fill price. Protective exit fills MUST use each mode’s existing Execution semantics (Backtest next-open; Simulation trustworthy live mark), never the TP/SL trigger level as fill price.
- **FR-006**: On a single processed candle, exit precedence MUST be: session/emergency/forced hard stops (existing) → stop loss → take profit → strategy exit; if TP and SL both trigger (unknowable intra-bar order), stop loss wins.
- **FR-007**: Omitting/disabling TP and/or SL MUST be supported at run configuration time (before/at start); disabled sides MUST NOT generate protective exits. Mid-position enable/disable or retune is out of scope.
- **FR-008**: Invalid TP/SL configuration for a long MUST be rejected before trading starts (fail closed) with an operator-visible reason.
- **FR-009**: Exit reasons for TP, SL, strategy exit, and existing session/forced stops MUST be distinguishable in journals/history/results. Protective TP/SL exits MUST be treated as non-strategy / forced-style closes so they do not increment `strategyFillCount` or consume `maxTrades` (Feature 003 strategy-driven fill limit).
- **FR-010**: While a long is open, operator-visible session state MUST include entry fill price and derived absolute TP/SL levels (when configured).
- **FR-011**: Repeated BUY/exit cycles MUST keep cash, holdings, and P&L consistent with fills and fees/slippage in Simulation and Backtest.
- **FR-012**: Feature 025 MUST document intentional Simulation vs Backtest execution/fill differences and MUST correct only accidental semantic inconsistencies affecting strategy/risk/TP/SL/accounting.
- **FR-013**: Feature 025 MUST minimally enrich strategy candle input with **OHLC** and MUST add a bounded set of approximately 3–4 additional conventional strategy/signal primitives with conceptual diversity (Stochastic, Keltner/ATR channel, ROC/Momentum, and relative volume only if the volume reliability gate passes). It MUST NOT add a plugin architecture, indicator library, or many MA variants.
- **FR-014**: A volume-based strategy MUST NOT be required unless XT candle volume is confirmed sufficiently reliable for both Backtest and Simulation semantics; otherwise it MUST be deferred.
- **FR-015**: New and existing strategies MUST remain advisory only; Controller and Risk remain authoritative.
- **FR-016**: UI changes MUST be minimal: show entry, position, TP/SL levels, and exit reason; MUST remain usable near 375px width; MUST NOT redesign Portfolio or add heavy charts/analytics.
- **FR-017**: Feature 025 MUST NOT expand Feature 014 recovery, Portfolio allocation/reservation machinery, per-symbol weight machinery, Settings architecture, comparison polish, execution abstraction redesign, or XT private write APIs.
- **FR-018**: Automated tests MUST cover TP, SL, strategy exit, same-candle precedence, disabled TP/SL, invalid config rejection, repeated cycles accounting, and registration/evaluation of each added strategy in Backtest (and Simulation where applicable).
- **FR-019**: After implementation, an MVP-1 acceptance validation MUST demonstrate Backtest → Simulation lifecycle with BUY → position → TP or SL or strategy EXIT → correct accounting → understandable history, creating new work only for concrete defects found.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can configure TP and/or SL and observe a Backtest long exit for each configured protective side with the correct exit reason in under one validation session.
- **SC-002**: The same protective exit behavior is demonstrable in Simulation on closed candles without tick infrastructure.
- **SC-003**: In fixture tests, when SL and TP both qualify on one candle, the closing exit reason is stop-loss 100% of the time.
- **SC-004**: In fixture tests, repeated entry/exit cycles (≥3) leave cash/holdings/P&L matching the sum of applied fills and costs.
- **SC-005**: Operators can point to a short written list of intentional Simulation vs Backtest differences and do not need to assume unexplained P&L gaps are random.
- **SC-006**: At least three additional registered strategies beyond the original five are selectable and produce deterministic signals under fixtures (volume strategy counted only if reliability gate passed).
- **SC-007**: On a ~375px layout, an operator can see open TP/SL levels and the exit reason after close without using a redesigned Portfolio or new primary navigation.
- **SC-008**: No Feature 025 change enables Real order placement or RealExecutionAdapter live fills.

## Scope Boundaries

### In scope

- Per-position fixed TP/SL for Simulation + Backtest
- Closed-candle TP/SL semantics (explicit)
- Precedence vs strategy and session exits
- Minimal UI visibility
- Document intentional Sim vs Backtest differences; fix accidental inconsistencies
- Bounded extra conventional strategies
- Tests and MVP-1 acceptance gate (validation exercise)

### Out of scope

- Trailing stops, multi-level TP, dynamic/ATR stops, mid-position stop management
- Tick/intrabar/WebSocket trading
- Real XT trading / Feature 015 work
- Torque / GE
- 014 recovery expansion
- Portfolio redesign / allocation expansion
- Advanced analytics / heavy charts
- Plugin indicator frameworks
- Short selling / multi-position / multi-symbol Real
- VPS/cloud deployment

## Key Entities *(include if feature involves data)*

- **Position protective levels**: entry-linked TP and/or SL trigger prices (or percent + derived price), active only while long.
- **Exit reason**: operator-visible classification for TP, SL, strategy exit, or existing session/forced stops.
- **Strategy primitive**: registered deterministic signal source with parameters (existing + new bounded set).
- **Mode semantics note**: documented intentional Simulation vs Backtest fill/price-selection differences.

## Assumptions

- Long-only, one open position per session remains the Stage-1 model.
- Closed-candle processing remains the Simulation worker model.
- Feature 008 defaults may optionally carry TP/SL **percentage** defaults without a Settings redesign.
- Market-data candles already expose high/low (and often volume); Feature 025 uses them for TP/SL triggers and OHLC strategy input without rebuilding Market Data.
- Portfolio allocation internals stay as implemented; operator focus remains cash, holdings, position, P&L, allocated capital.

## Dependencies

- Features 003–012 (Simulation, Backtest, Strategy, Risk, Portfolio, Execution, History) — DONE
- Feature 014 recovery — DONE and frozen
- Feature 015 — NOT in scope; consumes 025 outcomes later
