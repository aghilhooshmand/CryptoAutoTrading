# Feature Specification: Execution Abstraction

**Feature Branch**: `012-execution-abstraction`

**Created**: 2026-08-15

**Status**: Implemented

**Input**: User description (conversation context for Feature 012 — Execution Abstraction): Formalize one execution interface across Historical, Simulation, and future Real trading so Controller and Risk do not depend on which execution mode is active. Consolidate existing historical and simulation fill semantics without changing established Feature 003 Simulation or Feature 004 Backtest behavior. Historical keeps next-open (and established flatten) fill timing; Simulation keeps existing live-mark execution semantics; Backtest must not gain Portfolio dependency; Real execution is interface/stub only with actual XT/private exchange execution deferred to Feature 013+. Out of scope: XT private API, autonomous real-money trading, Risk semantic changes, Strategy changes, new operator-facing trading workflows.

## Clarifications

### Session 2026-08-15

- Q: How deep should Historical and Simulation consolidation go while preserving identical trading outcomes? → A: Shared fill economics and rejection sizing may be consolidated behind one contract; timing, price source, journal wiring, flatten orchestration, and Portfolio side effects remain mode-specific unless equivalence is proven by regression tests (Option B + constraint).
- Q: How reachable must the Real execution stub be in Feature 012? → A: Code/test only — Real adapter exists only in code/tests; not selectable from normal operator workflows until later real-trading features (Option A).
- Q: Must Simulation and Historical production fills go through the shared execution contract, or is extracting shared math while leaving separate call sites enough? → A: Both production Historical and Simulation strategy-fill paths must go through the shared execution contract; adapters keep their own timing, pricing, journaling, and allowed side effects (Option B).
- Q: Must Strategy Comparison’s historical evaluation use the same shared Historical execution path as Backtest? → A: Comparison historical fills must reuse the same Historical execution adapter/path as Backtest; Comparison-specific orchestration remains unchanged (Option A).
- Q: How should the Real stub report that execution is unavailable when tests invoke it? → A: Return the normal structured fill-failure result with stable reason `real_execution_unavailable`; never place an order or mutate trading/accounting state (Option A).

## Behavior locks (non-negotiable)

These locks MUST appear in planning and implementation and MUST be verified by regression before Feature 012 is marked DONE:

1. **No behavior change** to Simulation trading outcomes relative to Feature **003** (same fills, fees/slippage, reject codes, forced-close / unsafe-unflattened, journals, and Portfolio side effects already established).
2. **No behavior change** to Backtest trading outcomes relative to Feature **004** (same chronological fills, next-open timing, `approved_unexecutable` when no next candle, flatten semantics, journals, and summaries).
3. **Historical** execution MUST keep **next-open** fill semantics for strategy fills (and existing end-of-run / hard-stop flatten reference-price rules).
4. **Simulation** execution MUST keep existing **live** execution semantics (fill reference from the session’s established live/safe mark path—not historical next-open).
5. **Backtest / historical evaluation MUST NOT** gain a **Portfolio** dependency (no reserved/deployed binding, no Portfolio holdings updates from backtest fills).
6. **Real** execution in this feature is an **interface / stub only**; placing or managing real exchange orders and XT private integration are **deferred to Feature 013+**.

## Amendment 2026-08-17 — venue_order_id (minimum)

Feature 012 semantics for Historical/Simulation/Backtest are **unchanged**.

Minimum additive change: `FillResult` MAY include `venue_order_id` (generic).
Keep `xt_order_id` as a legacy alias until Feature 015 Kraken execution
replaces XT writes. Real Kraken order placement is **not** Feature 012 work;
it remains Feature 015 after 002+013 Kraken public/private-read.

- **FR-018**: `FillResult` MUST allow a venue-neutral `venue_order_id`.
  Simulation/Backtest fill outcomes MUST NOT change.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One execution contract for modes (Priority: P1)

As the platform maintainer, I want Historical and Simulation fills to share one clear execution contract so Controller and Risk stay mode-agnostic and we do not grow a second trading engine.

**Why this priority**: Without a single contract, fill logic continues to fork silently and Real cannot be added safely later.

**Independent Test**: After consolidation, run the existing Simulation and Backtest regression suites with fixed fixtures; compare fill prices, fees, slippage, reject codes, and decision outcomes to pre-012 baselines (no intentional deltas).

**Acceptance Scenarios**:

1. **Given** an approved Simulation BUY/SELL that previously filled, **When** the same session conditions are replayed under Feature 012, **Then** the fill quantities, prices, fees, slippage, and journal outcomes match the established Simulation behavior.
2. **Given** an approved Backtest BUY/SELL with a next candle available, **When** the same candle fixture is replayed under Feature 012, **Then** the fill uses the next candle’s open as reference (historical timing) and money outcomes match established Backtest behavior.
3. **Given** Controller and Risk have approved a non-HOLD signal, **When** execution is invoked for a production Simulation or Historical strategy fill, **Then** the fill goes through the shared execution contract (mode adapter supplies timing, pricing, journaling, and allowed side effects)—not a mode-private duplicate entry path.
4. **Given** duplicate or near-duplicate fill sizing / fee / reject logic existed across modes, **When** Feature 012 completes, **Then** that shared economics may be consolidated behind the contract while timing, price source, journal wiring, flatten orchestration, and Portfolio side effects stay mode-specific unless regressions prove equivalence.

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
3. **Given** Simulation fills that already update Portfolio holdings under Feature 009, **When** Feature 012 consolidates execution, **Then** that Simulation Portfolio side effect remains Simulation-scoped and is not copied into Backtest or Comparison.

---

### User Story 3b - Comparison shares Historical fills (Priority: P2)

As a platform maintainer, I want Strategy Comparison historical fills to use the same Historical execution path as Backtest so we do not keep a third fill fork.

**Why this priority**: Prevents silent semantic drift between Backtest and Comparison without expanding Comparison UX scope.

**Independent Test**: Run Comparison and Backtest fixtures that fill historically; assert both use next-open Historical semantics and Portfolio isolation; Comparison orchestration/UI unchanged.

**Acceptance Scenarios**:

1. **Given** a Comparison that evaluates historical strategy fills, **When** fills occur, **Then** they use the same Historical execution path as Backtest (next-open when applicable).
2. **Given** Feature 012 completes, **When** operators run Comparison as before, **Then** Comparison-specific orchestration (create/run/results presentation) remains unchanged aside from the shared Historical fill path.

---

### User Story 4 - Real execution stub only (Priority: P2)

As the platform maintainer, I want a Real execution placeholder behind the same contract so future XT private work has a single attachment point—without enabling real orders in this feature.

**Why this priority**: Sets the architecture for Phase C without violating “simulation before real money.”

**Independent Test**: Construct Real via code/tests; assert unavailable outcome and no exchange calls; confirm ordinary Simulation/Backtest create/run UI has no Real mode selection.


**Acceptance Scenarios**:

1. **Given** the shared execution contract, **When** Real mode is constructed in code or tests, **Then** a stub exists that participates in the same interface shape as Historical and Simulation.
2. **Given** an attempt to execute via Real in this feature (from tests/code), **When** a fill is requested, **Then** the result is the normal structured fill-failure with stable reason `real_execution_unavailable`, no exchange order is placed, and no trading/accounting state is mutated.
3. **Given** ordinary operator create/run workflows for Simulation and Backtest, **When** an operator configures a session or run, **Then** Real is not offered as a selectable execution mode until later real-trading features.

---

### Edge Cases

- Approved intent that cannot be filled under mode rules (dust, insufficient cash, conflicting position, missing next candle, unsafe mark) MUST keep established reason codes / outcomes per mode.
- Forced / end-of-run flatten MUST remain mode-correct (Simulation vs Historical reference rules) and is not required to share the strategy-fill contract entry unless regressions later prove a safe merge.
- Comparison runs that reuse historical evaluation MUST keep Historical semantics and Portfolio isolation, and MUST route historical strategy fills through the same Historical execution path as Backtest (Comparison-specific orchestration stays unchanged).
- Stub Real MUST NOT be used as a silent fallback that invents Simulation fills.
- Real stub invocations MUST return structured fill-failure with reason `real_execution_unavailable` and MUST NOT mutate trading or accounting state.
- Consolidation MUST NOT rewrite historical journal rows or frozen Simulation History results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose one shared execution contract used after Controller and Risk approval for trading intents that can produce fills.
- **FR-001a**: Production Historical and Simulation **strategy-fill** paths MUST invoke that shared contract (via mode adapters); adapters retain mode-owned timing, pricing, journaling, and allowed side effects. Flatten orchestration remains mode-specific unless equivalence is proven by regression (see FR-002a).
- **FR-001b**: Strategy Comparison historical strategy fills MUST reuse the same Historical execution adapter/path as Backtest; Comparison-specific orchestration (run lifecycle, UI, summaries) MUST remain unchanged aside from that shared fill path.
- **FR-002**: Historical and Simulation modes MUST both satisfy that contract while retaining their established price/timing policies (next-open historical vs live Simulation mark path).
- **FR-002a**: Shared fill economics and rejection sizing MAY be consolidated behind the contract; timing, price source, journal wiring, flatten orchestration, and Portfolio side effects MUST remain mode-specific unless equivalence is proven by regression tests.
- **FR-003**: Controller and Risk MUST remain authoritative and MUST NOT embed mode-specific fill timing (next-open vs live mark) inside strategy logic.
- **FR-004**: Feature 012 MUST NOT change established Feature 003 Simulation fill, fee/slippage, reject, forced-close, journal, or Portfolio side-effect behavior.
- **FR-005**: Feature 012 MUST NOT change established Feature 004 Backtest fill timing, fee/slippage, reject, `approved_unexecutable`, flatten, journal, or summary behavior.
- **FR-006**: Historical strategy fills MUST continue to use next-open reference pricing when the next candle exists.
- **FR-007**: Simulation strategy fills MUST continue to use the established live-session reference path (not historical next-open).
- **FR-008**: Backtest / historical evaluation MUST NOT depend on Portfolio reserved/deployed capital or holdings updates.
- **FR-009**: Simulation MAY continue to apply established Portfolio fill side effects; those side effects MUST remain Simulation-only.
- **FR-010**: A Real execution stub MUST exist behind the shared contract for code and tests, MUST NOT place exchange orders or call private XT trading APIs in this feature, and MUST NOT be selectable from normal operator workflows until later real-trading features.
- **FR-011**: Real stub execution MUST fail closed by returning the normal structured fill-failure result with stable reason `real_execution_unavailable`, MUST NOT place an exchange order, and MUST NOT mutate trading or accounting state (including Portfolio and mode ledgers).
- **FR-012**: Fee and adverse-slippage economics for Historical and Simulation MUST remain consistent with the shared money rules already established (no intentional economic model change in 012).
- **FR-013**: Execution reject reason codes that operators already rely on for Simulation and Backtest MUST remain stable unless a documented bugfix is explicitly in scope (default: no code renames).
- **FR-014**: Feature 012 MUST NOT introduce a second trading pipeline or allow strategies to mutate balances/positions directly.
- **FR-015**: Feature 012 MUST NOT implement XT account authentication, private balances, or live order placement (Feature 013+).
- **FR-016**: Feature 012 MUST NOT change Feature 010 Risk semantics, Feature Log Mode rules, or Simulation History freeze rules.
- **FR-017**: Regression evidence MUST demonstrate that representative Simulation and Backtest fixtures produce the same trading outcomes before vs after consolidation (behavior-preserving gate).

### Key Entities

- **Trading intent**: Approved BUY/SELL (or forced flatten) request after Controller/Risk—not a strategy-owned balance mutation.
- **Execution mode**: Historical, Simulation, or Real (stub)—selects price/timing policy and allowed side effects.
- **Fill outcome**: Success with quantity and economic fill details, or failure with a stable reason suitable for the decision journal (Real stub uses `real_execution_unavailable`).
- **Reference price policy**: Mode-owned rule for which price is used (next-open historical vs live Simulation mark path vs Real unavailable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the project’s established Simulation regression scenarios used as the Feature 012 gate still pass with unchanged expected fill/journal outcomes.
- **SC-002**: 100% of the project’s established Backtest fill-timing and pipeline regression scenarios used as the Feature 012 gate still pass with unchanged expected outcomes (including next-open and missing-next-candle cases).
- **SC-003**: In a controlled check with Portfolio capital present, completing a Backtest with fills leaves Portfolio reserved/available/holdings unchanged.
- **SC-004**: Attempting Real execution from code/tests yields a structured fill-failure with reason `real_execution_unavailable`, never places an exchange order, never mutates trading/accounting state, and ordinary operator workflows cannot select Real.
- **SC-005**: A reviewer can identify a single execution contract that production Historical and Simulation strategy fills both call through, and that Real stubs for tests, without reading strategy code for fill math.
- **SC-006**: No operator-facing Simulation or Backtest workflow requires new configuration solely to keep prior behavior (zero intentional UX change for ordinary create/run flows); Real is not added as an operator mode option in Feature 012.

## Assumptions

- Feature 012 is primarily an architectural consolidation for maintainers and future Real integration; it does not add a new primary operator product screen.
- Consolidation depth is Option B: shared fill math / rejection sizing only by default; mode-owned concerns stay mode-owned unless regressions prove a safer merge.
- Production Historical and Simulation strategy-fill paths must call through the shared contract; flatten orchestration stays mode-specific unless regressions prove equivalence.
- “No behavior change” is verified by existing automated regressions plus any thin new contract tests—not by redesigning trading economics.
- Strategy Comparison continues to use historical evaluation semantics and remains Portfolio-isolated for fills; its historical strategy fills share the Backtest Historical execution path while Comparison orchestration stays as established.
- Real mode is code/test-only in Feature 012; presence as a stub/contract participant is sufficient and it is not selectable from normal operator workflows until later real-trading features.
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
- Operator-facing Real trading mode selection or real-money execution UX (deferred to later real-trading features)
