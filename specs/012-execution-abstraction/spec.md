# Feature Specification: Execution Abstraction

**Feature Branch**: `012-execution-abstraction`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description (conversation context for Feature 012 — Execution Abstraction): Formalize one execution interface across Historical, Simulation, and future Real trading so Controller and Risk do not depend on which execution mode is active. Consolidate existing historical and simulation fill semantics without changing established Feature 003 Simulation or Feature 004 Backtest behavior. Historical keeps next-open (and established flatten) fill timing; Simulation keeps existing live-mark execution semantics; Backtest must not gain Portfolio dependency; Real execution is interface/stub only with actual XT/private exchange execution deferred to Feature 013+. Out of scope: XT private API, autonomous real-money trading, Risk semantic changes, Strategy changes, new operator-facing trading workflows.

## Behavior locks (non-negotiable)

These locks MUST appear in planning and implementation and MUST be verified by regression before Feature 012 is marked DONE:

1. **No behavior change** to Simulation trading outcomes relative to Feature **003** (same fills, fees/slippage, reject codes, forced-close / unsafe-unflattened, journals, and Portfolio side effects already established).
2. **No behavior change** to Backtest trading outcomes relative to Feature **004** (same chronological fills, next-open timing, `approved_unexecutable` when no next candle, flatten semantics, journals, and summaries).
3. **Historical** execution MUST keep **next-open** fill semantics for strategy fills (and existing end-of-run / hard-stop flatten reference-price rules).
4. **Simulation** execution MUST keep existing **live** execution semantics (fill reference from the session’s established live/safe mark path—not historical next-open).
5. **Backtest / historical evaluation MUST NOT** gain a **Portfolio** dependency (no reserved/deployed binding, no Portfolio holdings updates from backtest fills).
6. **Real** execution in this feature is an **interface / stub only**; placing or managing real exchange orders and XT private integration are **deferred to Feature 013+**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One execution contract for modes (Priority: P1)

As the platform maintainer, I want Historical and Simulation fills to share one clear execution contract so Controller and Risk stay mode-agnostic and we do not grow a second trading engine.

**Why this priority**: Without a single contract, fill logic continues to fork silently and Real cannot be added safely later.

**Independent Test**: After consolidation, run the existing Simulation and Backtest regression suites with fixed fixtures; compare fill prices, fees, slippage, reject codes, and decision outcomes to pre-012 baselines (no intentional deltas).

**Acceptance Scenarios**:

1. **Given** an approved Simulation BUY/SELL that previously filled, **When** the same session conditions are replayed under Feature 012, **Then** the fill quantities, prices, fees, slippage, and journal outcomes match the established Simulation behavior.
2. **Given** an approved Backtest BUY/SELL with a next candle available, **When** the same candle fixture is replayed under Feature 012, **Then** the fill uses the next candle’s open as reference (historical timing) and money outcomes match established Backtest behavior.
3. **Given** Controller and Risk have approved a non-HOLD signal, **When** execution is invoked, **Then** the same upstream approval path is used regardless of whether the active mode is Simulation or Historical—only the execution mode’s price/timing policy differs.
4. **Given** duplicate or near-duplicate fill sizing / fee / reject logic existed across modes, **When** Feature 012 completes, **Then** Historical and Simulation both satisfy the shared execution contract without introducing a parallel pipeline.

---

### User Story 2 - Preserve Historical vs Simulation semantics (Priority: P1)

As an operator, I want Backtests to remain deterministic on historical candles and Simulations to continue using live-session execution, so experiments stay comparable and live sessions stay truthful to their existing rules.

**Why this priority**: Mixing next-open into Simulation or live marks into Backtest would silently invalidate research and operator trust.

**Independent Test**: Fixture Backtest proves next-open fills and `approved_unexecutable` when the next candle is missing; Simulation tick with a safe mark fills at that mark path; neither path adopts the other’s price policy.

**Acceptance Scenarios**:

1. **Given** a Backtest signal on candle N with candle N+1 present, **When** Risk approves, **Then** execution fills using candle N+1 open (historical next-open), not a live quote.
2. **Given** a Backtest signal on the last candle with no next candle, **When** Risk would otherwise approve, **Then** the decision remains `approved_unexecutable` (or the established equivalent) and no invented fill occurs.
3. **Given** a RUNNING Simulation with an established safe mark path for fills, **When** Risk approves a trade, **Then** execution uses that live Simulation reference path—not next-open historical timing.
4. **Given** a Simulation forced close / flatten situation without a trustworthy mark, **When** stop/flatten runs, **Then** established unsafe / unflattened behavior is preserved (no invented market price).

---

### User Story 3 - Keep Backtest free of Portfolio (Priority: P1)

As an operator, I want historical Backtests to stay isolated from Portfolio reserved/deployed capital and holdings books so research runs do not mutate live capital identity.

**Why this priority**: Portfolio coupling in Backtest would break isolation and Feature 009/010 boundaries.

**Independent Test**: Run a Backtest that would buy/sell; assert Portfolio reserved, available, and holdings are unchanged; Simulation-only Portfolio fill-apply regressions still pass separately.

**Acceptance Scenarios**:

1. **Given** a Portfolio with reserved allocations and holdings, **When** a Backtest run completes with fills, **Then** Portfolio reserved, available, deployed, and holdings are unchanged by that run.
2. **Given** Feature 010 portfolio-aware Risk is active for Simulation, **When** a Backtest evaluates Risk, **Then** Backtest does not require or enable Portfolio binding / portfolio max-loss context as a dependency of historical execution.
3. **Given** Simulation fills that already update Portfolio holdings under Feature 009, **When** Feature 012 consolidates execution, **Then** that Simulation Portfolio side effect remains Simulation-scoped and is not copied into Backtest.

---

### User Story 4 - Real execution stub only (Priority: P2)

As the platform maintainer, I want a Real execution placeholder behind the same contract so future XT private work has a single attachment point—without enabling real orders in this feature.

**Why this priority**: Sets the architecture for Phase C without violating “simulation before real money.”

**Independent Test**: Selecting or constructing Real mode returns a clear “not available / stub” outcome; no private exchange credentials or order placement are required or invoked.

**Acceptance Scenarios**:

1. **Given** the shared execution contract, **When** Real mode is referenced, **Then** a stub exists that participates in the same interface shape as Historical and Simulation.
2. **Given** an attempt to execute via Real in this feature, **When** a fill is requested, **Then** no exchange order is placed and the outcome is an explicit unavailable/not-implemented style rejection (not a silent simulated fill labeled as real).
3. **Given** Feature 013+ work has not started, **When** operators use Simulation and Backtest, **Then** those modes remain the only executable trading modes with real fills in-product.

---

### Edge Cases

- Approved intent that cannot be filled under mode rules (dust, insufficient cash, conflicting position, missing next candle, unsafe mark) MUST keep established reason codes / outcomes per mode.
- Forced / end-of-run flatten MUST remain mode-correct (Simulation vs Historical reference rules).
- Comparison runs that reuse historical evaluation MUST keep Historical semantics and Portfolio isolation.
- Stub Real MUST NOT be used as a silent fallback that invents Simulation fills.
- Consolidation MUST NOT rewrite historical journal rows or frozen Simulation History results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose one shared execution contract used after Controller and Risk approval for trading intents that can produce fills.
- **FR-002**: Historical and Simulation modes MUST both satisfy that contract while retaining their established price/timing policies (next-open historical vs live Simulation mark path).
- **FR-003**: Controller and Risk MUST remain authoritative and MUST NOT embed mode-specific fill timing (next-open vs live mark) inside strategy logic.
- **FR-004**: Feature 012 MUST NOT change established Feature 003 Simulation fill, fee/slippage, reject, forced-close, journal, or Portfolio side-effect behavior.
- **FR-005**: Feature 012 MUST NOT change established Feature 004 Backtest fill timing, fee/slippage, reject, `approved_unexecutable`, flatten, journal, or summary behavior.
- **FR-006**: Historical strategy fills MUST continue to use next-open reference pricing when the next candle exists.
- **FR-007**: Simulation strategy fills MUST continue to use the established live-session reference path (not historical next-open).
- **FR-008**: Backtest / historical evaluation MUST NOT depend on Portfolio reserved/deployed capital or holdings updates.
- **FR-009**: Simulation MAY continue to apply established Portfolio fill side effects; those side effects MUST remain Simulation-only.
- **FR-010**: A Real execution stub MUST exist behind the shared contract and MUST NOT place exchange orders or call private XT trading APIs in this feature.
- **FR-011**: Real stub execution MUST fail closed with an explicit unavailable/not-implemented outcome rather than pretending a Simulation fill is real.
- **FR-012**: Fee and adverse-slippage economics for Historical and Simulation MUST remain consistent with the shared money rules already established (no intentional economic model change in 012).
- **FR-013**: Execution reject reason codes that operators already rely on for Simulation and Backtest MUST remain stable unless a documented bugfix is explicitly in scope (default: no code renames).
- **FR-014**: Feature 012 MUST NOT introduce a second trading pipeline or allow strategies to mutate balances/positions directly.
- **FR-015**: Feature 012 MUST NOT implement XT account authentication, private balances, or live order placement (Feature 013+).
- **FR-016**: Feature 012 MUST NOT change Feature 010 Risk semantics, Feature Log Mode rules, or Simulation History freeze rules.
- **FR-017**: Regression evidence MUST demonstrate that representative Simulation and Backtest fixtures produce the same trading outcomes before vs after consolidation (behavior-preserving gate).

### Key Entities

- **Trading intent**: Approved BUY/SELL (or forced flatten) request after Controller/Risk—not a strategy-owned balance mutation.
- **Execution mode**: Historical, Simulation, or Real (stub)—selects price/timing policy and allowed side effects.
- **Fill outcome**: Success with quantity and economic fill details, or failure with a stable reason suitable for the decision journal.
- **Reference price policy**: Mode-owned rule for which price is used (next-open historical vs live Simulation mark path vs Real unavailable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the project’s established Simulation regression scenarios used as the Feature 012 gate still pass with unchanged expected fill/journal outcomes.
- **SC-002**: 100% of the project’s established Backtest fill-timing and pipeline regression scenarios used as the Feature 012 gate still pass with unchanged expected outcomes (including next-open and missing-next-candle cases).
- **SC-003**: In a controlled check with Portfolio capital present, completing a Backtest with fills leaves Portfolio reserved/available/holdings unchanged.
- **SC-004**: Attempting Real execution in this feature never places an exchange order and always yields an explicit unavailable outcome.
- **SC-005**: A reviewer can identify a single execution contract that Historical and Simulation both satisfy, and that Real stubs, without reading strategy code for fill math.
- **SC-006**: No operator-facing Simulation or Backtest workflow requires new configuration solely to keep prior behavior (zero intentional UX change for ordinary create/run flows).

## Assumptions

- Feature 012 is primarily an architectural consolidation for maintainers and future Real integration; it does not add a new primary operator product screen.
- “No behavior change” is verified by existing automated regressions plus any thin new contract tests—not by redesigning trading economics.
- Strategy Comparison continues to use historical evaluation semantics and remains Portfolio-isolated for fills.
- Real mode may be unreachable from ordinary UI in this feature; presence as a stub/contract participant is sufficient.
- XT public market data remains available for Simulation marks as today; private XT is out of scope.
- Features 003, 004, 009, 010, and 011 remain the source of truth for Simulation, Backtest, Portfolio, Risk, and History behaviors respectively.

## Out of Scope

- XT private API, credentials, account balances, live order placement/cancel (013+)
- Paper-trading hardening / crash resume (014)
- Confirmed real-money execution UX (015)
- Changing Dual EMA or other strategies
- Changing Risk catalogs or portfolio max-loss rules
- Changing Decision Log Mode or History freeze rules
- New multi-active Simulation sessions
- Inventing fills when marks or next candles are unavailable
