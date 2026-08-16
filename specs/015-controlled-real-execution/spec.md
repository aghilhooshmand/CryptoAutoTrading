# Feature Specification: Real-Money Manual/Confirmed Execution

**Feature Branch**: `015-controlled-real-execution`  
**Created**: 2026-08-16  
**Status**: Clarified (session 2026-08-16); remediated I1–I4 (2026-08-16)
**Feature ID**: `015`  
**Input**: Roadmap Controlled Real MVP (MVP-2) after Feature 025 + MVP-1 gate DONE

## Context

Stage-1 paper path (Backtest → Simulation) is closed: Features 012–014 frozen
infrastructure, Feature 013 private read path, Feature 025 per-position TP/SL,
MVP-1 acceptance passed. Feature **015** is the first **Controlled Real**
milestone on XT. It is **not** autonomous trading.

## Clarifications

### Session 2026-08-16

- Q: Should Controlled Real reuse the existing Simulation session model with a
  distinct Real mode, or use a separate Real-only session entity? → A: Reuse
  the same session/pipeline with an explicit Real mode; keep
  execution/accounting mode-specific. Same Strategy → Controller → Risk →
  Execution architecture; confirmation gate before exposure-increasing Real
  orders; no second trading engine. Real sessions MUST NOT write Simulation
  Portfolio holdings; Real fills/order state MUST come from XT reconciliation;
  Real vs Simulation provenance MUST stay explicit; Real MUST be unmistakable
  in API/UI/history; RealExecutionAdapter is the only route from an approved
  Real intent to XT.
- Q: For Controlled Real MVP, which XT order style should confirmed entries and
  automatic exits use? → A: Market orders only for both entries and exits.
  Submission MUST NEVER be treated as a successful fill; actual XT order/fill
  state MUST be reconciled. Limit orders are deferred until after Controlled
  Real MVP is proven.
- Q: What hard upper bound should Controlled Real MVP enforce for session
  capital (allocated / max position)? → A: Hard maximum **50 USDT** allocated
  capital, with maxPositionSize ≤ allocatedCapital. Operator may configure any
  lower amount. Enforced fail-closed before submitting an XT entry order. MVP
  safety cap only — raising/removing requires an explicit future product
  decision after Controlled Real is validated.
- Q: What should happen if a Real BUY stays waiting for operator confirmation
  and is never confirmed? → A: Pending confirmation expires after **5
  minutes**. On expiry, discard the intent without placing any XT order; keep
  the session running. A future entry requires a fresh Strategy → Controller →
  Risk cycle. Even within the TTL, confirmation MUST perform final
  safety/current-state validation immediately before XT submission.
- Q: After a backend restart while a Controlled Real session was running, what
  should the system do? → A: Enter a dedicated blocked recovery state. Never
  auto-resume Real trading. Discard all pending entry confirmations. Reconcile
  XT balances/orders/fills vs local session via Feature 013. No
  strategy-generated orders while blocked. Operator must explicitly Resume
  after reconcile proves safe, or Stop/Flatten using reconciled trustworthy XT
  state. Resume MUST re-run current safety/risk checks; if reconcile is
  incomplete/contradictory, Resume stays unavailable (fail closed). Do **not**
  extend Feature 014 Simulation auto-recovery into Real for this MVP.

### Remediation locks (2026-08-16 analyze I1–I4)

- I1: XT free USDT gate before Real entry submit (FR-004a).
- I2: Real `startingCapital` / initial `cash` are local budget only — not XT
  cash; actual balance/post-trade from reconcile (FR-004b).
- I3: Partial fill → record actual exposure + block strategy trading until
  Resume/Stop (FR-006b). Not “ignore partial / full-fill-only.”
- I4: ≤5s sync poll allowed; timeout must not forget the order — unsettled
  block + later reconcile before any new order (FR-006c).

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
3. **Given** a pending confirmation older than 5 minutes, **When** expiry
   runs, **Then** the intent is discarded with no XT order and the session
   stays running.
4. **Given** confirmation succeeds within TTL, **When** final pre-submit
   validation passes and XT accepts the order, **Then** local state is
   reconciled from exchange/account truth (Feature 013 read path), not from
   optimism alone.
5. **Given** confirm within TTL, **When** final pre-submit validation fails,
   **Then** no XT order is placed and the pending intent is cleared or
   rejected fail-closed.

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

1. **Given** Real session create, **When** allocatedCapital > 50 USDT or
   maxPositionSize > allocatedCapital (or multi-pair/position), **Then** create
   is rejected with a clear reason.
2. **Given** a valid Real session, **When** operating, **Then** at most one
   open long exists for that session.
3. **Given** Real mode UI, **When** the operator views Auto Trading, **Then**
   Real is unmistakable vs Simulation (no Portfolio redesign required).
4. **Given** a pending or confirmed entry path, **When** capital would exceed
   the 50 USDT MVP cap, **Then** XT entry submission is blocked fail-closed.

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

- Confirmation pending while mark becomes unsafe/stale — block confirm via
  final pre-submit validation; do not place XT order.
- Pending confirmation TTL (5 minutes) elapses — discard intent; session
  continues; no XT order.
- Partial XT fill — record actual filled exposure from reconcile evidence;
  enter fail-closed / reconciliation-blocked (no normal strategy trading)
  until operator Resume after safe reconcile or Stop/Flatten (FR-006b).
- Place/reconcile poll timeout with known or possible XT order — do **not**
  forget the order; enter unsettled/blocking; later reconcile must determine
  XT outcome before any new order (FR-006c).
- Unexpected XT order states — normalize when known; otherwise fail closed /
  blocked until reconcile.
- XT free USDT below intended Real entry notional — block confirm/submit
  fail-closed; no order (FR-004a).
- Session stop during waiting-for-confirmation — discard pending; no XT order.
- Protective exit and session hard-stop same candle (Feature 025 precedence
  preserved: session/emergency → SL → TP → strategy).
- Credential missing or Feature 013 errors (`timestamp_invalid`, rate limit).
- Attempt to enable autonomous (unconfirmed) Real entries — must remain out of
  scope / rejected.
- Limit-order placement requested — reject / unavailable in MVP (market only).
- Exchange ack without fill confirmation — remain unsettled until reconcile;
  never promote submission to filled.
- Restart during Real session — dedicated blocked recovery; never auto-resume;
  discard pending confirms; XT reconcile via 013; operator Resume (after safe
  reconcile + safety/risk re-check) or Stop/Flatten; do not reuse 014 Sim
  auto-recovery (FR-011).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Feature 015 MUST enable Controlled Real on the **same** session
  and trading pipeline as Simulation (Strategy → Controller → Risk → Execution)
  with an explicit Real mode; it MUST NOT introduce a second trading engine.
  Execution and accounting MUST remain mode-specific.
- **FR-001a**: Real sessions MUST NOT write Simulation Portfolio holdings.
  Real vs Simulation provenance MUST remain explicit in API, UI, journals, and
  history. Real mode MUST be unmistakable to operators.
- **FR-002**: Exposure-increasing Real entries MUST require explicit operator
  confirmation after Controller and Risk approval, before any XT placement.
- **FR-002a**: A pending Real BUY confirmation MUST expire after **5 minutes**.
  On expiry, discard the intent with **no** XT order; the Real session MUST
  remain running. Any later entry MUST require a fresh Strategy → Controller →
  Risk approval cycle (not reuse of the expired pending intent).
- **FR-002b**: Even within the confirmation TTL, operator confirm MUST re-run
  final safety / current-state validation immediately before XT submission
  (fail closed if unsafe/stale/invalid).
- **FR-003**: TP/SL exits, exposure-reducing strategy exits, and emergency/STOP
  flatten (when safely executable) MUST NOT require the entry confirmation
  gate.
- **FR-004**: Real sessions MUST enforce one trading pair, one open position,
  and capital bounds: **allocatedCapital ≤ 50 USDT** (hard MVP safety cap) and
  **0 < maxPositionSize ≤ allocatedCapital**, fail closed on invalid config.
  Operators MAY configure any lower allocated amount. Raising or removing the
  50 USDT cap requires an explicit future product decision after Controlled
  Real is validated. Cap enforcement MUST run before submitting an XT entry
  order (including before/at confirmation completion).
- **FR-004a**: Before submitting a Real exposure-increasing XT entry, the
  system MUST fail closed unless Feature 013 balance reads show sufficient
  **free** quote (USDT) for the intended notional. Session
  `allocatedCapital` / `maxPositionSize` (and local budget fields) MUST still
  apply; they MUST NOT authorize an entry the exchange free balance cannot
  cover. Missing/failed/stale balance reads MUST fail closed (no place).
- **FR-004b**: For Real sessions, `startingCapital` and initial session `cash`
  are **local budget / configuration** values only. They MUST NOT be presented
  or treated as actual XT cash. Actual available balance and post-trade
  cash/position MUST come from XT reconciliation (Feature 013 / FR-006).
- **FR-005**: **RealExecutionAdapter** MUST be the only route from an approved
  Real intent to XT. Simulation/Backtest paths MUST remain unchanged in
  behavior intent and MUST NOT place Real orders.
- **FR-006**: Local Real fills and order state MUST come from XT reconciliation
  via Feature 013 private reads (and write acknowledgements as specified in
  plan); the system MUST NOT invent fills, prices, or balances, and MUST NOT
  treat Simulation mark/next-open paper fills as Real truth. **Order
  submission MUST NEVER be treated as a successful fill.**
- **FR-006a**: Controlled Real MVP MUST use **market orders only** for both
  exposure-increasing entries and automatic exits (TP/SL, reducing strategy
  exit, emergency/STOP flatten when safely executable). Limit orders are out
  of scope until after Controlled Real MVP is proven.
- **FR-006b**: When XT reports a **partial** fill, the system MUST record the
  actual filled quantity/price as Real exposure from reconcile evidence, then
  enter a fail-closed / reconciliation-blocked session state. Normal
  strategy-generated trading MUST NOT continue while blocked. Operator MUST
  Resume only after reconcile proves safe, or Stop/Flatten using reconciled
  trustworthy XT state.
- **FR-006c**: RealExecutionAdapter MAY use a synchronous place+reconcile poll
  budget of **at most 5 seconds**. On timeout (or other unclear outcome) the
  system MUST NOT forget a submitted/possible XT order: persist order identity
  when known, enter an unsettled/blocking state, and forbid new orders until
  subsequent reconciliation determines the actual XT outcome. Timeout MUST NOT
  invent a fill or clear exposure blindly.
- **FR-007**: Real mode MUST be unmistakable in the operator UI and history;
  Portfolio redesign is out of scope.
- **FR-008**: Feature 015 MUST NOT implement autonomous (unconfirmed) Real
  entries; architecture SHOULD allow a later move to automatic entries under
  hard risk limits without a second pipeline.
- **FR-009**: Per-position TP/SL semantics from Feature 025 MUST apply to Real
  protective **trigger** evaluation unless a Real-specific constraint is
  explicitly specified; Real **fill** prices MUST follow XT reconciliation
  (FR-006), not Simulation mark inventiveness.
- **FR-010**: Automated tests MUST cover confirmation gate, auto exit paths,
  config bounds, Portfolio isolation (no Sim portfolio writes), reconcile
  failure modes, Real blocked-recovery/resume/stop, and UI/API Real
  distinctness without requiring live XT in unit tests (use fakes/mocks); any
  live smoke is optional and gated on credentials.
- **FR-011**: On backend restart (and on in-session unsettled/partial-block
  paths per FR-006b/FR-006c), a Controlled Real session MUST use dedicated Real
  **blocked recovery behavior** on the shared `RECOVERY_BLOCKED` state (or
  equivalent non-trading blocked occupation). The system MUST NEVER auto-resume
  Real trading. All pending entry confirmations MUST be discarded on restart
  recovery entry. The system MUST reconcile XT balances, orders/fills, and
  local session state via Feature 013 private capabilities. While blocked, no
  strategy-generated orders may execute (and no new Real orders until settle).
  The operator MUST explicitly **Resume** only after reconciliation proves the
  state safe, or **Stop/Flatten** using reconciled trustworthy XT state. Resume
  MUST re-run relevant current safety/risk checks before trading continues; if
  reconciliation is incomplete or contradictory, Resume MUST remain unavailable
  (fail closed). Feature 015 MUST NOT extend Feature 014 Simulation
  auto-recovery machinery into Real trading for this MVP.

### Key Entities

- **Session (mode=real)**: Same session lifecycle as Simulation, with Real mode
  flag/label; includes waiting-for-confirmation when applicable. Local
  startingCapital/initial cash are budget/config only (not XT cash). Does not
  share Simulation Portfolio holdings mutations.
- **PendingEntryConfirmation**: Approved exposure-increasing BUY awaiting
  operator confirm/decline before RealExecutionAdapter.
- **RealOrderReconcileView**: Normalized XT order/account snapshot used to
  update Real local truth.

## Success Criteria *(mandatory)*

- **SC-001**: An operator can complete one confirmed Real entry and one
  automatic protective or strategy exit on a tiny session in a supervised
  validation pass (or fully mocked equivalent in CI).
- **SC-002**: No Real BUY reaches XT without confirmation in fixture tests
  (100% of exposure-increasing cases); expired pendings never place orders;
  confirm-time validation failures never place orders.
- **SC-003**: Invalid multi-position / oversized capital configs (including
  allocatedCapital > 50 USDT) are rejected before trading starts; XT entry is
  never submitted when the MVP cap would be violated.
- **SC-004**: Simulated XT failures and submission-only acks never produce
  invented local fills; filled/partial exposure requires reconcile evidence;
  partial fills leave the session blocked; poll timeout retains order identity
  when known and blocks new orders until later reconcile settles outcome.
- **SC-007**: Fixture tests reject or omit limit-order Real placement in MVP.
- **SC-005**: UI and API clearly distinguish Real from Simulation (including
  history/provenance) without a new primary nav or Portfolio redesign.
- **SC-006**: Fixture tests prove Real session fills do not mutate Simulation
  Portfolio holdings.
- **SC-008**: After simulated restart, Real sessions are blocked (no strategy
  orders) until explicit Resume after successful reconcile, or Stop/Flatten;
  incomplete reconcile keeps Resume unavailable.

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
- Limit orders (deferred post–Controlled Real MVP)
- Portfolio UX redesign
- Torque / GE
- Expanding Feature 014 Simulation auto-recovery into Real (blocked-recovery
  for Real is specified separately; do not reuse 014 auto-resume)
- Trailing stops, ticks, volume strategies
