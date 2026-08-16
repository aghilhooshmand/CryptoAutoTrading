# Feature Specification: Real-Money Manual/Confirmed Execution

**Feature Branch**: `015-controlled-real-execution`  
**Created**: 2026-08-16  
**Status**: Draft  
**Feature ID**: `015`  
**Input**: Roadmap Controlled Real MVP (MVP-2) after Feature 025 + MVP-1 gate DONE

## Context

Stage-1 paper path (Backtest → Simulation) is closed: Features 012–014 frozen
infrastructure, Feature 013 private read path, Feature 025 per-position TP/SL,
MVP-1 acceptance passed. Feature **015** is the first **Controlled Real**
milestone on XT. It is **not** autonomous trading.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmed real entry (Priority: P1)

As an operator, I want exposure-increasing Real BUY intents to wait for my
explicit confirmation before XT placement so I never auto-enter real money
without knowingly approving size and symbol.

**Why this priority**: Capital protection; primary Controlled Real differentiator.

**Independent Test**: Configure a tiny Real session; strategy/Controller/Risk
approve BUY; UI shows waiting-for-confirmation; only after confirm does
RealExecutionAdapter attempt XT; rejection/cancel leaves no phantom position.

**Acceptance Scenarios**:

1. **Given** Controller and Risk approve a Real BUY, **When** Execution reaches
   the confirmation gate, **Then** no XT order is placed until the operator
   confirms.
2. **Given** a pending confirmation, **When** the operator declines or the
   session stops, **Then** no Real fill is invented and no order is left
   assumed open.
3. **Given** confirmation succeeds, **When** XT accepts the order, **Then**
   local state is reconciled from exchange/account truth (Feature 013 read
   path), not from optimism alone.

---

### User Story 2 - Automatic protective and reducing exits (Priority: P1)

As an operator, I want TP/SL, strategy exits that reduce/close exposure, and
emergency/STOP flatten to execute without waiting for entry-style confirmation
(when a safe execution path exists) so open Real risk can be reduced quickly.

**Why this priority**: Same risk model as Simulation/Backtest protective path;
confirmation is for increasing exposure only.

**Independent Test**: Open Real long (via confirmed entry); hit TP or SL or
strategy SELL or emergency stop; assert exit path does not require the entry
confirmation gate; reconcile after.

**Acceptance Scenarios**:

1. **Given** an open Real long with TP/SL configured, **When** protective
   levels trigger under closed-candle rules aligned with Feature 025, **Then**
   the exit may proceed automatically through Controller → Risk → Real
   Execution.
2. **Given** strategy SELL that closes/reduces the session position, **When**
   Controller and Risk approve, **Then** confirmation is not required for that
   reducing exit.
3. **Given** emergency or STOP flatten with a safe executable path, **When**
   the operator stops, **Then** flatten does not wait for entry confirmation.

---

### User Story 3 - Bounded Real session shape (Priority: P1)

As an operator, I want Real sessions limited to one pair, one open position,
tiny capital, and short/local supervision so blast radius stays small.

**Why this priority**: Roadmap MVP-2 non-negotiables before any autonomy.

**Independent Test**: Attempt to configure multi-position or oversized capital;
assert fail-closed validation; successful sessions enforce single long and
capital caps.

**Acceptance Scenarios**:

1. **Given** Real session create, **When** config violates one-pair / one-
   position / capital bounds, **Then** create is rejected with a clear reason.
2. **Given** a valid Real session, **When** operating, **Then** at most one
   open long exists for that session.
3. **Given** Real mode UI, **When** the operator views Auto Trading, **Then**
   Real is unmistakable vs Simulation (no Portfolio redesign required).

---

### User Story 4 - Reconcile over assume (Priority: P2)

As an operator, I want XT order/account state reconciled after Real actions so
local ledgers do not claim success the exchange did not confirm.

**Why this priority**: Fail-safe and constitution; Feature 013 is the read
authority.

**Independent Test**: Simulate XT accept vs reject vs timeout; local state
matches reconcile outcome; no fabricated fills.

**Acceptance Scenarios**:

1. **Given** an XT placement attempt, **When** the exchange rejects or timing
   is unclear, **Then** the system fails closed and does not invent a fill.
2. **Given** a successful XT fill, **When** reconcile runs, **Then** session
   cash/position align with private account/order reads within defined rules.

---

### Edge Cases

- Confirmation pending while mark becomes unsafe/stale.
- Partial fills / unexpected XT order states (normalize; fail closed where
  unknown).
- Session stop during waiting-for-confirmation.
- Protective exit and session hard-stop same candle (Feature 025 precedence
  preserved: session/emergency → SL → TP → strategy).
- Credential missing or Feature 013 errors (`timestamp_invalid`, rate limit).
- Attempt to enable autonomous (unconfirmed) Real entries — must remain out of
  scope / rejected.
- Restart during Real session — prefer fail closed / blocked over inventing
  recovery beyond what 014 patterns safely allow for Real (specify reconcile
  rules; do not expand 014 paper recovery architecture without need).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Feature 015 MUST enable Controlled Real on the existing single
  trading pipeline (Controller → Risk → Execution → Portfolio/Accounting); it
  MUST NOT introduce a second trading engine.
- **FR-002**: Exposure-increasing Real entries MUST require explicit operator
  confirmation after Controller and Risk approval.
- **FR-003**: TP/SL exits, exposure-reducing strategy exits, and emergency/STOP
  flatten (when safely executable) MUST NOT require the entry confirmation
  gate.
- **FR-004**: Real sessions MUST enforce one trading pair, one open position,
  and tiny configurable capital bounds (fail closed on invalid config).
- **FR-005**: RealExecutionAdapter MUST place XT orders only for approved Real
  intents; Simulation/Backtest paths MUST remain unchanged in behavior intent.
- **FR-006**: Local Real state MUST be reconciled from XT private read
  capabilities (Feature 013); the system MUST NOT invent fills, prices, or
  balances.
- **FR-007**: Real mode MUST be unmistakable in the operator UI; Portfolio
  redesign is out of scope.
- **FR-008**: Feature 015 MUST NOT implement autonomous (unconfirmed) Real
  entries; architecture SHOULD allow a later move to automatic entries under
  hard risk limits without a second pipeline.
- **FR-009**: Per-position TP/SL semantics from Feature 025 MUST apply to Real
  protective exits unless a Real-specific fill constraint is explicitly
  specified and tested.
- **FR-010**: Automated tests MUST cover confirmation gate, auto exit paths,
  config bounds, reconcile failure modes, and UI Real distinctness without
  requiring live XT in unit tests (use fakes/mocks); any live smoke is optional
  and gated on credentials.

### Key Entities

- **RealSession**: Operator-supervised Real session config and lifecycle state
  (including waiting-for-confirmation).
- **PendingEntryConfirmation**: Approved BUY awaiting operator confirm/decline.
- **RealOrderReconcileView**: Normalized XT order/account snapshot used to
  update local truth.

## Success Criteria *(mandatory)*

- **SC-001**: An operator can complete one confirmed Real entry and one
  automatic protective or strategy exit on a tiny session in a supervised
  validation pass (or fully mocked equivalent in CI).
- **SC-002**: No Real BUY reaches XT without confirmation in fixture tests
  (100% of exposure-increasing cases).
- **SC-003**: Invalid multi-position / oversized capital configs are rejected
  before trading starts.
- **SC-004**: Simulated XT failures never produce invented local fills.
- **SC-005**: UI clearly distinguishes Real from Simulation without a new
  primary nav or Portfolio redesign.

## Assumptions

- Feature 025 TP/SL and MVP-1 gate are DONE.
- Feature 013 private read APIs are available for reconcile.
- RealExecutionAdapter exists as a stub today and will be completed for XT
  writes under this feature’s contracts.
- Closed-candle evaluation remains acceptable for Real MVP (ticks out of
  scope unless explicitly added later).

## Out of Scope

- Autonomous Real entries
- Multi-pair / multi-position Real sessions
- Portfolio UX redesign
- Torque / GE
- Expanding Feature 014 paper recovery architecture unless a concrete Real
  defect requires a minimal shared fix
- Trailing stops, ticks, volume strategies
