# Feature Specification: Portfolio & Capital Allocation Core

**Feature Branch**: `009-portfolio-capital-allocation`

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Portfolio & Capital Allocation Core — Build the authoritative portfolio and capital-allocation foundation for CryptoAutoTrading. Track and clearly distinguish total portfolio equity, cash, available capital, allocated/reserved capital, capital currently deployed in positions, realized P&L, unrealized P&L, and positions. Support explicit capital allocations so capital can later be assigned safely to different strategies, trading programs, or Torque branches without allowing total allocated or deployed capital to exceed available portfolio capital. Capital ownership and accounting must be independent from strategy logic. Strategies remain advisory only and must never directly modify portfolio balances or positions. All trading continues through Controller → Risk → Execution. Preserve compatibility with existing Simulation and Backtest accounting where applicable, while establishing a reusable portfolio/capital model for future Simulation, Real Money, and Torque. Enable later scenarios such as full assignment of capital to one strategy/program, division across multiple strategies/programs, unused capital remaining available, and independent allocation performance while belonging to one portfolio. Prevent overspending, double allocation, negative available capital, and inconsistent accounting. Persist effective allocation/accounting state for inspection and reproducibility. Provide operator-facing portfolio/allocation UI under the existing product structure following docs/UI_UX_STANDARDS.md. Do not implement XT private/account integration, real-money execution, leverage, short selling, margin, multi-exchange portfolios, Torque grammar/program execution, Grammatical Evolution, automatic capital optimization, or strategy ranking. This feature is the shared capital/accounting foundation for later Features 010–023."

## Clarifications

### Session 2026-08-14

- Q: How should the operator establish the local portfolio’s initial cash / equity in Feature 009? → A: Operator explicitly sets portfolio starting cash/equity in Portfolio (controlled funding); later cash adjustments use controlled portfolio funding actions that keep capital invariants
- Q: In Feature 009, before Simulation/Real Money are bound to allocations, what should “capital deployed in positions” and the positions list represent? → A: First-class portfolio fields that remain zero/empty in 009 until a later feature binds trading activity; still shown clearly so the capital model is complete
- Q: How should available capital be defined relative to cash, allocated/reserved capital, and deployed capital? → A: `available = cash − reserved`; deployed is a distinct reported category (0 in 009); reserved cannot exceed cash
- Q: May two different allocations both reference the same strategy or program label at the same time? → A: Yes — multiple allocations may share the same optional target reference if capital invariants hold; targets are labels, not unique ownership keys
- Q: When the operator reduces portfolio cash through a funding adjustment, what must happen if the new cash would be below total reserved capital? → A: Reject the reduction; require release/resize of allocations first; leave prior state unchanged

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect authoritative portfolio capital (Priority: P1)

As a local operator, I want a Portfolio view that shows my portfolio’s capital
picture—total equity, cash, available capital, allocated/reserved capital,
capital deployed in positions, realized P&L, unrealized P&L, and positions—so
that I can trust one authoritative accounting surface instead of inferring
capital from strategy screens.

**Why this priority**: Without a clear, consistent portfolio capital model and
inspection surface, allocations and later multi-strategy / Torque / real-money
work have no shared foundation.

**Independent Test**: Fund a portfolio with known starting cash, open Portfolio,
and confirm each capital category is visible, labeled, and internally consistent
(available cannot go negative; totals reconcile).

**Acceptance Scenarios**:

1. **Given** the operator has not yet funded the local portfolio, **When** they
   open Portfolio, **Then** they can set an explicit starting cash/equity via a
   controlled funding action before allocations are meaningful.
2. **Given** a local portfolio exists with known cash and no open positions,
   **When** the operator opens Portfolio, **Then** they see total equity, cash,
   available capital, allocated/reserved capital, deployed capital, realized
   P&L, unrealized P&L, and positions (empty or listed) with clear labels and
   units. In Feature 009 before trading is bound to the portfolio, deployed
   capital is 0 and the positions list is empty (still visible as such).
3. **Given** the portfolio has reserved allocations (and, in later features,
   open positions), **When** the operator views Portfolio, **Then**
   allocated/reserved capital and deployed capital are shown as distinct
   concepts and do not silently collapse into one ambiguous “used” number.
4. **Given** any displayed portfolio snapshot, **When** the operator checks
   the capital identity, **Then** available capital is never negative and the
   snapshot does not imply that strategies own or invented the capital.

---

### User Story 2 - Create and manage explicit capital allocations (Priority: P1)

As a local operator, I want to create, adjust, and release explicit capital
allocations (for example one allocation using all available capital, or several
allocations splitting capital across future strategy/program uses) so that
unused capital stays available and no allocation can overspend the portfolio.

**Why this priority**: Explicit allocations are the constitutionally required
capital-ownership model; without them the feature does not deliver its core
purpose.

**Independent Test**: From a portfolio with known available capital, create
two valid allocations that sum to less than or equal to available capital,
attempt an overspending allocation and confirm rejection, then release or
reduce an allocation and confirm available capital increases accordingly.

**Acceptance Scenarios**:

1. **Given** available capital of C (cash minus existing reserved), **When** the
   operator creates one allocation of size C for a single target label, **Then**
   the allocation is accepted, available capital becomes 0, and
   allocated/reserved capital equals C (absent deployment).
2. **Given** available capital of C, **When** the operator creates multiple
   allocations whose sizes sum to ≤ C, **Then** each allocation is recorded
   independently with its own identity and size, unused remainder stays
   available, and the portfolio still shows one shared equity base.
3. **Given** available capital of C, **When** the operator attempts an
   allocation that would make total reserved capital exceed cash, **Then** the
   system rejects the change with a clear reason and leaves the prior
   portfolio/allocation state unchanged.
4. **Given** an existing allocation that is not fully deployed, **When** the
   operator reduces or releases it within allowed rules, **Then** reserved
   capital decreases and available capital increases by the released amount
   without creating negative available capital.
5. **Given** any allocation create/resize/release attempt, **When** validation
   fails (over-allocation, invalid size, inconsistent state), **Then** no
   partial corrupt update is persisted.

---

### User Story 3 - Inspect allocation-level accounting within one portfolio (Priority: P2)

As a local operator, I want each allocation to show its own reserved size and
performance/accounting summary while still belonging to the same portfolio so
that I can compare how capital was assigned without treating allocations as
separate portfolios or strategy-owned wallets.

**Why this priority**: Independent allocation accounting is required for the
stated future scenarios, but the portfolio capital model and safe reservation
rules are the MVP; allocation inspection can follow immediately after.

**Independent Test**: Create at least two allocations with different sizes,
inspect each allocation’s reserved capital and accounting summary, and confirm
portfolio totals still reconcile.

**Acceptance Scenarios**:

1. **Given** two allocations A and B under one portfolio, **When** the
   operator inspects each, **Then** each shows its own identity, reserved
   capital, and allocation-level accounting fields provided by this feature
   (at minimum reserved size; performance fields when activity exists).
2. **Given** those allocations, **When** the operator returns to the portfolio
   summary, **Then** portfolio totals remain the single source of truth and
   allocation figures do not double-count portfolio equity.
3. **Given** an allocation with no trading activity yet, **When** the
   operator inspects it, **Then** the UI still makes the reserved capital and
   membership in the parent portfolio obvious.

---

### User Story 4 - Persist portfolio and allocation state for inspection and reproducibility (Priority: P1)

As a local operator, I want portfolio and allocation accounting state persisted
so that after restart I can inspect the same effective capital picture and
later features can rely on a stable foundation.

**Why this priority**: A non-persisted capital model cannot support
reproducibility or later Simulation / Real Money / Torque binding.

**Independent Test**: Create portfolio capital and allocations, restart or
reload the application, and confirm the same effective portfolio/allocation
state is still available for inspection.

**Acceptance Scenarios**:

1. **Given** the operator has established portfolio capital and one or more
   allocations, **When** they reload the application, **Then** the Portfolio
   view shows the same effective capital categories and allocation records.
2. **Given** a rejected invalid allocation change, **When** the operator
   reloads, **Then** the last valid persisted state is still present (the
   rejected change was never applied).

---

### Edge Cases

- Allocation size of zero or negative → rejected; prior state unchanged.
- Sum of allocation reserves would exceed cash → rejected with a clear
  over-allocation reason.
- Funding reduction that would make cash below total reserved → rejected;
  operator must release/resize allocations first; prior state unchanged.
- Reducing an allocation below capital already deployed for that allocation
  (when deployment exists) → rejected or constrained so accounting stays
  consistent (no negative available; no silent under-reservation).
- Concurrent or repeated submit of the same allocation change → must not
  double-apply reservations.
- Empty positions list when flat → shown clearly as no open positions, not as
  missing data. In Feature 009 this is the normal state until later binding.
- Corrupt or inconsistent stored portfolio state on load → fail closed to a
  safe recoverable posture with a clear operator warning (do not invent
  capital to “fix” the books).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an authoritative local portfolio capital
  model that distinguishes at least: total portfolio equity, cash, available
  capital, allocated/reserved capital, capital currently deployed in
  positions, realized P&L, unrealized P&L, and positions. Deployed capital and
  positions MUST be first-class fields even when zero/empty. In Feature 009,
  before Simulation/Real Money/Torque binding, deployed capital MUST remain 0
  and the positions list MUST remain empty unless a later feature writes them
  through the authoritative pipeline (not via strategy-side mutation).
- **FR-001a**: The operator MUST establish and adjust portfolio cash/equity
  through explicit controlled Portfolio funding actions (initial set and later
  adjustments). Feature 008 Settings MUST NOT silently become the portfolio
  ledger. Funding actions MUST preserve capital invariants (no negative
  available capital; no inconsistent totals). A funding reduction that would
  make `cash < reserved` MUST be rejected with a clear reason; the operator
  MUST release or resize allocations first. Prior valid state MUST remain
  unchanged.
- **FR-002**: The system MUST support explicit capital allocations that reserve
  portfolio capital for named uses (strategy, trading program, Torque branch,
  or operator label) without transferring ownership of capital to strategy
  logic. An optional target reference MUST NOT be required to be unique across
  allocations; multiple allocations MAY share the same target reference when
  total reserved capital still respects FR-003.
- **FR-003**: Capital identity for Feature 009 MUST be:
  `available = cash − reserved`, with `reserved ≥ 0`, `available ≥ 0`, and
  `reserved ≤ cash`. Deployed capital is a distinct reported category and MUST
  NOT be subtracted again from available in this feature’s undeployed
  foundation (deployed remains 0 until later binding). Double allocation of the
  same capital MUST be prevented (total reserved across allocations cannot
  exceed cash).
- **FR-004**: Strategies MUST remain advisory only. Strategy logic MUST NEVER
  directly create, invent, or modify portfolio balances, reservations, or
  positions. Any future trading that uses portfolio capital MUST continue
  through Controller → Risk → Execution.
- **FR-005**: Each allocation MUST have a stable identity and reserved size,
  and MUST remain a child of the parent portfolio for accounting (not a
  separate portfolio). Identity is the allocation record itself, not the
  optional target reference.
- **FR-006**: The system MUST allow the operator to create, inspect, adjust
  (resize), and release allocations subject to the capital invariants in
  FR-003.
- **FR-007**: The system MUST persist the effective portfolio and allocation
  accounting state needed for inspection and reproducibility after restart.
- **FR-008**: Invalid allocation or portfolio updates MUST be rejected with a
  clear reason and MUST leave the last valid persisted state unchanged.
- **FR-009**: Existing Simulation and Backtest accounting behavior MUST remain
  compatible for this feature’s delivery: session/run effective configurations
  and historical results MUST NOT be rewritten by introducing the portfolio
  model. Full migration of Simulation/Backtest fill ledgers onto the new
  portfolio ledger is out of scope for this feature unless needed for a thin,
  non-breaking compatibility bridge.
- **FR-010**: The operator MUST have a Portfolio-facing UI under the existing
  primary Portfolio area to inspect portfolio capital categories and manage
  allocations. Feature-specific UI behavior is limited to portfolio/allocation
  presentation and flows; general form/feedback/responsive rules inherit from
  `docs/UI_UX_STANDARDS.md` and constitution XIV.
- **FR-011**: Portfolio and allocation amounts MUST be presented with clear
  labels and units. Simulation vs any future real-money portfolio context MUST
  remain distinguishable when both could appear; this feature MUST NOT enable
  real-money trading.
- **FR-012**: This feature MUST NOT implement: XT private/account integration;
  real-money execution; leverage; short selling; margin; multi-exchange
  portfolios; Torque grammar/program execution; Grammatical Evolution;
  automatic capital optimization; or strategy ranking.

### Key Entities

- **Portfolio**: The single local capital container for this feature’s v1
  scope. Holds authoritative equity/cash/available/reserved/deployed P&L and
  position summary state.
- **Capital Snapshot**: A coherent operator-visible (and persisted) view of
  portfolio capital categories at a point in time for inspection and
  reproducibility.
- **Allocation**: An explicit reservation of portfolio capital for a named
  use (label and optional strategy/program reference). Tracks reserved size
  and allocation-level accounting while remaining part of the parent
  portfolio.
- **Position (portfolio view)**: An open holdings summary associated with the
  portfolio capital model (quantity/side/symbol context as applicable). Does
  not grant strategies authority to mutate balances.
- **Allocation Target Reference**: Optional non-authoritative reference
  (e.g., strategy id or program label) describing intended future use of an
  allocation. Does not execute trades or move capital by itself. Need not be
  unique across allocations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can open Portfolio and, within one minute, identify
  equity, cash, available, allocated/reserved, deployed, realized P&L,
  unrealized P&L, and positions for the local portfolio without consulting
  strategy screens.
- **SC-002**: In a portfolio with known available capital C, the operator can
  successfully create a valid split of allocations summing to ≤ C, and every
  attempt to reserve more than allowed is rejected with no change to prior
  state (verified in automated tests).
- **SC-003**: After creating allocations and reloading the application, 100%
  of the last valid portfolio capital categories and allocation records remain
  inspectable (no silent loss of reserved capital state).
- **SC-004**: Automated checks prove `available = cash − reserved`, available
  never goes negative, reserved never exceeds cash, and double-reservation of
  the same capital cannot succeed.
- **SC-005**: Existing Simulation and Backtest regression suites that encode
  current session/run accounting remain green after this feature lands (no
  unintended rewrite of historical effective configs).
- **SC-006**: Portfolio primary workflows for inspect + allocate remain usable
  around 375px width, with clear units/labels and non-hover-only help where
  capital terms are non-obvious.

## Assumptions

- **Single local portfolio for v1**: One operator machine hosts one
  authoritative local portfolio container for this feature (no multi-user or
  multi-portfolio product yet).
- **Initial funding**: Portfolio cash/equity is established by explicit
  operator funding in the Portfolio area (not auto-imported from Settings or
  mirrored from an active Simulation session).
- **Denomination**: Portfolio and allocation amounts use the same quote-style
  money representation already used by Simulation/Backtest (USDT-oriented
  operator amounts). Roadmap “€500” examples are illustrative of split
  scenarios, not a separate fiat ledger in this feature.
- **Foundation-first integration**: Feature 009 establishes the reusable
  portfolio/allocation model and operator UI. Existing Simulation and Backtest
  keep their current session/run accounting unless a thin compatibility bridge
  is required. Binding live Simulation/Real Money/Torque sessions to
  allocations is expected in later features. Until then, portfolio deployed
  capital stays 0 and positions stay empty while remaining visible.
- **Allocations are reservations, not trading sessions**: Creating or resizing
  an allocation does not start, stop, or authorize trading and does not place
  orders.
- **Capital identity (v1)**: `available = cash − reserved`; deployed is
  reported separately and stays 0 in Feature 009; reserved cannot exceed cash.
- **Long-only / no leverage in this model’s v1 constraints**: Consistent with
  project non-goals, the portfolio/allocation model does not introduce short,
  margin, or leveraged capital semantics.
- **Primary navigation**: Portfolio remains the existing primary area for this
  UI (no new top-level nav item).
- **UI standards inheritance**: Global form, feedback, responsive, and
  accessibility defaults come from `docs/UI_UX_STANDARDS.md`; this spec only
  states portfolio/allocation-specific presentation needs.
- **Dependencies**: Builds on application foundation, market/simulation/
  backtest capital concepts already in the product, and constitution rules on
  capital protection, advisory strategies, and portfolio/allocation authority
  (especially I, V, XXXIV).

## Non-Goals

- XT private account sync or exchange balance import
- Real-money enablement or execution
- Leverage, short selling, margin, multi-exchange portfolios
- Torque grammar/runtime and Grammatical Evolution
- Automatic capital optimizers or strategy ranking dashboards
- Replacing Feature 008 Settings (defaults remain defaults; they do not become
  the portfolio ledger)
- Full rewrite of historical Simulation/Backtest journals onto a new ledger in
  this feature
