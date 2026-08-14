# Feature Specification: Advanced Risk Management

**Feature Branch**: `010-advanced-risk-management`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Feature 010 — Advanced Risk Management. Audit-approved MVP: keep one shared Risk authority on the existing pipeline (Market Data → Strategy → Controller → Risk → Execution → Portfolio/Accounting). Catalog and reuse existing session risk/control/execution reject and stop reasons; extend with portfolio-aware codes. Wire Simulation Risk to Feature 009 available / reserved / deployed and per-allocation exposure limits (deferred from 009). Add one clear Simulation Portfolio-level loss stop. Optional simple per-symbol exposure limit. Persist effective risk configuration on session/run create; Settings remain defaults only. Do not create a second risk engine for Portfolio, Backtest, Torque, or real trading. New portfolio-aware rules apply to Simulation; Backtest continues to reuse shared session Risk only. Out of scope: XT private API, real-money execution, reconciliation, execution-abstraction rewrite, Torque/GE-specific risk engines, autonomous trading, daily loss limits, unifying session cash with Portfolio USDT into one wallet."

## Clarifications

### Session 2026-08-14 (audit → specify lock)

- Q: Which MVP slice? → A: Approved audit §5 — shared Risk catalog/reuse; Simulation↔Portfolio capital gates; per-allocation deployed caps; one portfolio max-loss stop; optional simple per-symbol exposure; persist effective risk config; Backtest gets session Risk continuity only for new portfolio rules.
- Q: Unify session cash and Portfolio USDT in 010? → A: **No.** Keep dual ledgers. Risk **reads** Portfolio figures for gates; does not rewrite Feature 003 session cash as the only wallet.
- Q: Daily loss / portfolio drawdown chart stops? → A: **Out of 010.** Session loss (existing) + one Portfolio max-loss stop only. Drawdown remains a Backtest report metric unless a later feature promotes it to a stop.
- Q: Must every session bind an allocation? → A: **Optional.** If the operator binds an allocation, enforce that allocation’s reserved size vs deployed on BUYs. If unbound, enforce Portfolio `available` vs `allocated_capital` at create/start only (BUY does not re-check `available` — see clarify session).
- Q: Where do operators configure new risk fields? → A: Simulation create/start (and Settings defaults for those fields). Portfolio shows clear rejection/stop reasons and capital figures — not a second primary Risk app area.

### Session 2026-08-14 (clarify)

- Q: When Portfolio max-loss is evaluated during an active Simulation, how is “loss from baseline” measured if valuation becomes incomplete after start? → A: Freeze metric kind at start (known-value equity if complete, else USDT). Loss = baseline − current under that kind. If current cannot be computed, reject new BUYs; do not invent a portfolio-loss stop from missing prices.
- Q: On an active Simulation BUY, what Portfolio capital figure must Risk compare the intended trade against? → A: When allocation-bound, BUY must fit allocation remaining (`reserved − deployed` for that binding). When unbound, Portfolio `available` is enforced at create/start only — BUY does not re-check `available`. Do not subtract `deployed` from `available`. Session cash / allocated / max-position remain separate session gates.
- Q: If the operator resizes or releases a Portfolio allocation while a Simulation bound to it is still active, what must happen? → A: Reject release while any session is bound. Allow resize only when new reserved ≥ current deployed for that binding.
- Q: When several Risk rejection rules would all fail the same Simulation BUY, which reason must journals and the operator see? → A: Fixed precedence; return only the first failing catalog reason. Stable reason **codes** are separate from human-readable **messages**. Order: emergency → session inactive / already-triggered hard session stops → unsafe/missing mark → portfolio max-loss uncomputable (BUY block) or portfolio max-loss reached → max trades / profit target / session max loss → conflicting position → allocation exposure (if bound) → per-symbol concentration → session sizing / insufficient balance (if at Risk; else Execution keeps its codes).
- Q: When the optional per-symbol weight cap is set, what denominator and valuation rules must Risk use for the projected post-BUY weight? → A: Weight = projected post-BUY known-value of that non-quote asset ÷ known-value Portfolio equity. Stale follows Feature 002. Missing/incomplete valuation fails closed (reject increasing exposure). Quote asset (USDT) is excluded from the cap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulation respects Portfolio capital (Priority: P1)

As an operator, I want Simulation Risk to refuse trades that the Simulation
Portfolio cannot fund under Feature 009 capital rules, so that reserved and
available USDT actually protect capital.

**Why this priority**: Without this, Feature 009 reservations are accounting
labels while Risk still sizes only against session cash — the main gap the
audit identified.

**Independent Test**: Fund Portfolio USDT, reserve part via an allocation,
start Simulation with allocated capital that would violate available (or bind
an allocation and attempt oversize exposure). Confirm create/start or BUY is
rejected with an explicit portfolio-aware reason; session journals do not
silently invent balances.

**Acceptance Scenarios**:

1. **Given** Portfolio quote cash C and reserved R (`available = C − R`),
   **When** the operator tries to start Simulation with
   `allocated_capital > available`, **Then** start is rejected with a clear
   portfolio-capital reason and no active session begins.
2. **Given** an active Simulation **bound** to an allocation with remaining
   capacity M (`reserved − deployed`), **When** Risk reviews a BUY whose
   intended notional would exceed M, **Then** Risk rejects with an explicit
   allocation-exposure reason; balances and positions are unchanged by that
   signal.
3. **Given** an active Simulation **not** bound to an allocation, **When**
   Risk reviews a BUY, **Then** Portfolio `available` is not re-checked on
   that BUY (create/start already enforced it); session cash / allocated /
   max-position gates still apply.
4. **Given** Feature 003 session journals and Feature 009 fill-apply rules,
   **When** Risk rejects, **Then** no strategy write to balances occurs and
   Pipeline order remains Controller → Risk → Execution → Portfolio.

---

### User Story 2 - Per-allocation exposure limits (Priority: P1)

As an operator, I want a Simulation bound to a Portfolio allocation to be
unable to deploy more than that allocation’s reserved size, so that sleeves
are real risk limits — not just labels.

**Why this priority**: Feature 009 explicitly deferred per-allocation deployed
limits to Feature 010.

**Independent Test**: Create allocation reserved 200 USDT, bind a Simulation
to it, attempt exposure that would make allocation-deployed > 200. Reject with
allocation-exposure reason.

**Acceptance Scenarios**:

1. **Given** allocation A with reserved size S and a session bound to A,
   **When** a BUY would make that allocation’s deployed exposure exceed S,
   **Then** Risk rejects and does not execute.
2. **Given** a session **not** bound to an allocation, **When** trading,
   **Then** per-allocation deployed caps do not invent a binding; Portfolio
   available / portfolio-level stops still apply.
3. **Given** resize or release of an allocation while a session bound to it is
   active, **When** the operator submits release, **Then** release is rejected
   with a clear reason and the allocation remains. **When** they resize,
   **Then** the new reserved size is accepted only if it is ≥ current deployed
   for that binding; otherwise the resize is rejected and prior reserved size
   is unchanged.

---

### User Story 3 - One Portfolio max-loss stop (Priority: P1)

As an operator, I want one Simulation Portfolio-level maximum loss stop so
that losses across simulation trading cannot quietly exhaust the Portfolio
beyond a configured bound.

**Why this priority**: Audit called for one clear portfolio stop rather than
many overlapping drawdown/daily mechanisms in the first slice.

**Independent Test**: Configure portfolio max loss, run Simulation until
Portfolio known-value loss from the persisted session-start baseline reaches
the bound; session stops; further strategy entries do not execute.

**Acceptance Scenarios**:

1. **Given** a configured Portfolio max-loss bound and a frozen start baseline
   metric, **When** `baseline − current` under that same metric kind reaches
   the bound, **Then** Risk/stop ends the active Simulation with an explicit
   portfolio-loss reason (forced flatten rules remain those of Feature 003
   when a safe price exists).
2. **Given** the frozen metric kind cannot be computed for the current book
   (e.g. equity baseline but equity incomplete), **When** Risk evaluates,
   **Then** it does not invent prices or declare a portfolio-loss stop from
   missing marks; it rejects new BUYs until the metric is computable again
   (other session stops still apply).
3. **Given** Backtest or Comparison runs, **When** they execute, **Then** this
   Portfolio max-loss stop does **not** apply (no live Simulation Portfolio
   book for those runs in 010).

---

### User Story 4 - Optional per-symbol exposure (Priority: P2)

As an operator, I want an optional simple cap on how large one non-quote asset
may be in the Simulation Portfolio so that concentration is bounded without a
full risk-policy product.

**Why this priority**: Useful guardrail; secondary to capital gates and
portfolio max loss.

**Independent Test**: Set a per-symbol max weight; attempt a BUY that would
push that asset’s known-value weight above the cap; Risk rejects.

**Acceptance Scenarios**:

1. **Given** an optional per-symbol max weight W of known-value Portfolio
   equity, **When** a BUY would make that non-quote asset’s **projected
   post-BUY** weight exceed W, **Then** Risk rejects with a
   concentration/per-symbol reason.
2. **Given** the optional limit is unset, **When** trading, **Then** no
   per-symbol weight cap is invented.
3. **Given** missing public price or incomplete known-value equity for the
   check, **When** the cap is set, **Then** Risk rejects increasing exposure
   (fail closed) — never treat unknown value as zero to pass. Stale
   last-known prices follow Feature 002 semantics. USDT (quote) is not
   subject to this cap.

---

### User Story 5 - Shared reasons and persisted effective risk config (Priority: P1)

As an operator, I want consistent risk rejection/stop reasons and a frozen
copy of the risk settings that applied to each Simulation, so that journals
and reloads stay explainable and Settings changes cannot rewrite history.

**Why this priority**: Constitution requires traceability and Settings-as-
defaults; the audit found an informal reason-code scatter.

**Independent Test**: Reject via a new portfolio reason; confirm journal shows
a stable code/message. Change Settings after create; historical session still
shows the original effective risk configuration.

**Acceptance Scenarios**:

1. **Given** any Controller/Risk/Execution reject or hard stop in Simulation,
   **When** the operator inspects the decision/stop, **Then** they see a
   stable reason **code** and a separate human-readable **message** from the
   shared catalog (existing session codes remain; new portfolio codes are
   added — no silent renames that break Feature 003/004 regression meaning).
2. **Given** a BUY that violates more than one Risk rule, **When** Risk
   rejects, **Then** journals record only the first failing reason under the
   fixed precedence in FR-002a.
3. **Given** Settings defaults for new risk fields, **When** a Simulation is
   created, **Then** effective risk configuration is copied and persisted on
   that session; later Settings edits do not alter it.
4. **Given** Backtest/Comparison, **When** created, **Then** existing session-
   style risk fields continue to persist as today; new portfolio-only fields
   are not required on those artifacts in 010.

---

### Edge Cases

- Portfolio unfunded (`available` 0) → Simulation start with positive allocated
  capital rejected.
- Portfolio `warning` (fill-apply or corrupt) → Risk still fail-closes; does
  not invent balances or prices to approve a BUY.
- Bound allocation released while session running → release rejected; allocation
  and binding remain until the session is no longer bound (e.g. stopped).
- Bound allocation resized below current deployed → resize rejected; prior
  reserved size unchanged.
- Partial equity / stale prices → portfolio loss and per-symbol checks never
  invent mark values; stale may be used only under Feature 002 stale rules
  already established for valuation.
- Portfolio max-loss baseline frozen as equity, then equity becomes incomplete
  → reject new BUYs; do not invent a portfolio-loss stop until the equity
  metric is computable again (or another hard stop fires).
- Emergency stop / session max loss / profit target / max trades / duration →
  continue to work; portfolio rules are additional gates, not replacements.
- Risk approves but Execution cannot size (dust/insufficient session cash) →
  Execution still fail-closes; journal records Execution reason (catalogued).
- Multiple longs / multi-session → 010 assumes the existing product model
  (at most one active Simulation); do not invent multi-session global freeze
  beyond stopping that active session on portfolio max loss.
- Multiple Risk rules would reject the same BUY → journals show only the first
  failing reason under FR-002a precedence; codes stay stable and distinct from
  messages.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep a **single** Risk authority on the pipeline
  Market Data → Strategy → Controller → Risk → Execution → Portfolio /
  Accounting. Feature 010 MUST NOT add a second risk engine for Portfolio,
  Backtest, Torque, or real trading.
- **FR-002**: The system MUST maintain a **shared catalog** of rejection and
  stop outcomes. Each outcome MUST expose a stable machine **reason code**
  separate from a human-readable **message**. The catalog MUST cover existing
  Feature 003/004 meanings (session inactive, emergency, stale/unsafe market
  data, max trades, profit target, max session loss, conflicting position,
  insufficient balance / sizing, duration, etc.) and new portfolio-aware codes
  (insufficient portfolio available at create/start, allocation exposure
  exceeded, allocation release/resize blocked while bound, portfolio max loss,
  portfolio max-loss metric uncomputable, per-symbol exposure exceeded, and
  related validation codes). Existing codes MUST keep their meaning for
  regression continuity (no silent renames).
- **FR-002a**: When multiple Risk rules would reject the same signal, Risk MUST
  evaluate in fixed precedence and return **only the first** failing reason
  (code + message). Precedence MUST be: emergency → session inactive /
  already-triggered hard session stops → unsafe/missing mark → portfolio
  max-loss metric uncomputable (BUY block) or portfolio max-loss reached →
  max trades / profit target / session max loss → conflicting position →
  allocation exposure (if bound) → per-symbol concentration → session sizing /
  insufficient balance when evaluated at Risk (otherwise Execution retains its
  catalogued codes).
- **FR-003**: Existing session Risk behavior (profit target, max session loss,
  max trades, unsafe mark, long-only conflicts as enforced today through
  Risk and/or Execution) MUST remain for Simulation and, where already
  specified, for Backtest — consolidated or reused, not reimplemented as a
  divergent copy.
- **FR-004**: Simulation create/start MUST reject when
  `allocated_capital >` Feature 009 Portfolio `available` (quote cash minus
  reserved), with a clear reason. Reserved allocations MUST continue to
  satisfy Feature 009 `reserved ≤ quote_cash`. Feature 009 identity remains:
  `available = quote_cash − reserved`; `deployed` is reported separately and
  MUST NOT be subtracted again from `available` for this check.
- **FR-005**: On Simulation BUY review, Portfolio capital gates are:
  (a) if the session is bound to an allocation, Risk MUST reject when the
  intended BUY would make that binding’s deployed exceed the allocation’s
  reserved size (equivalently, intended notional must fit
  `reserved − current_deployed` for that binding);
  (b) if the session is unbound, Risk MUST NOT re-check Portfolio `available`
  on each BUY — that check is create/start only (FR-004).
  Session cash, `allocated_capital`, and `max_position_size` gates remain.
  Strategies MUST NEVER bypass Risk to change balances.
- **FR-006**: A Simulation MAY optionally bind to one Feature 009 allocation.
  When bound, deployed exposure attributable to that binding MUST NOT exceed
  the allocation’s reserved size. Unbound sessions MUST NOT invent a binding.
  While a session remains bound to an allocation, Portfolio MUST reject
  release of that allocation. Resize of that allocation MUST be accepted only
  when the new reserved size is ≥ current deployed for that binding; otherwise
  the resize MUST be rejected and prior state unchanged.
- **FR-007**: The operator MAY configure one **Portfolio max-loss** bound for
  Simulation (absolute quote-currency amount and/or rate of a persisted
  baseline defined in Assumptions). At Simulation start the system MUST freeze
  a baseline metric kind and value (known-value equity if `equityComplete`,
  else quote cash). Loss MUST be `baseline − current` under that frozen kind
  only. When the bound is reached under a computable current metric, the
  active Simulation MUST stop with an explicit portfolio-loss reason. When the
  current metric cannot be computed under the frozen kind, Risk MUST reject
  new BUYs and MUST NOT invent a portfolio-loss stop from missing prices.
  This stop MUST NOT apply to Backtest or Strategy Comparison in Feature 010.
- **FR-008**: The operator MAY optionally configure a simple **per-symbol**
  maximum weight for non-quote holdings: projected post-BUY known-value of
  that asset divided by known-value Portfolio equity. When set, Risk MUST
  reject BUYs that would exceed it. When unset, no weight cap is applied.
  Stale prices MUST follow Feature 002 semantics. Missing or incomplete
  valuation MUST fail closed (reject increasing exposure); unknown MUST NOT
  be treated as zero to pass. The quote asset (USDT) MUST be excluded from
  this cap.
- **FR-009**: Allocated-capital and max-position-size limits MUST remain
  enforced fail-closed. Risk MUST be able to reject on portfolio/session
  capital grounds before Execution; Execution MUST still refuse unsafe sizing
  (dust / insufficient session cash) so a Risk approve cannot invent a fill.
- **FR-010**: Effective risk configuration for a Simulation (session risk
  fields plus new portfolio-aware fields and binding) MUST be materialized and
  persisted at create/start. Settings MUST only supply defaults for new
  configurations. Later Settings changes MUST NOT alter existing or historical
  sessions/runs.
- **FR-011**: Decision journals and stop records MUST expose catalog reason
  codes and messages for new portfolio rejects/stops. Operators MUST be able
  to see Simulation mode and risk outcomes without opening a separate real-
  money or XT private surface.
- **FR-012**: Feature 010 MUST NOT implement XT private APIs, real-money
  execution, exchange reconciliation, Torque/GE-specific risk engines,
  autonomous trading, daily loss limits, or a full execution-adapter rewrite.
  Unifying session cash with Portfolio USDT into one wallet is out of scope.

### Key Entities

- **Shared Risk Catalog**: Stable reason codes and messages for control, risk,
  execution, and stop outcomes.
- **Effective Risk Configuration**: Persisted per Simulation (and existing
  per Backtest/Comparison session-style fields); includes portfolio-aware
  fields when applicable.
- **Allocation Binding** (optional): Link from a Simulation session to one
  Feature 009 allocation for exposure capping.
- **Portfolio Risk Baseline**: Persisted reference used for the Portfolio
  max-loss stop (see Assumptions).
- **Risk Decision**: Approve/reject (+ optional stop trigger) after Controller,
  before Execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Automated tests prove Simulation create/start is rejected when
  `allocated_capital >` Portfolio available, with a portfolio-capital reason.
- **SC-002**: Automated tests prove a BUY that would exceed a bound
  allocation’s reserved size is rejected and does not change positions.
- **SC-003**: Automated tests prove reaching the configured Portfolio max-loss
  bound stops the active Simulation with a portfolio-loss reason; Backtest
  runs are unaffected by that stop.
- **SC-004**: When an optional per-symbol weight cap is set, automated tests
  prove a violating BUY is rejected; when unset, behavior matches today’s
  absence of that cap.
- **SC-005**: Feature 003 Simulation and Feature 004 Backtest regression
  suites that protect existing session risk semantics stay green.
- **SC-006**: After create, changing Settings risk defaults does not change
  the persisted effective risk configuration of an existing Simulation.
- **SC-007**: Within one local demo, an operator can cause at least one
  portfolio-aware Risk rejection and read a clear reason in the UI/journals
  without using XT credentials or real-money controls.
- **SC-008**: Primary Simulation configure + risk feedback remains usable
  around 375px width; help for new risk fields is not hover-only
  (`docs/UI_UX_STANDARDS.md`).

## Assumptions

- One active Simulation session remains the product model for 010 global /
  portfolio stops (stop that session; do not invent multi-session orchestration).
- Dual ledger remains: Feature 003 session cash vs Feature 009 Portfolio USDT.
  Risk consults Portfolio for gates; fill-apply rules from 009 remain.
- **BUY Portfolio capital**: Bound session → intended BUY must fit allocation
  remaining (`reserved − deployed` for that binding). Unbound session →
  Portfolio `available` enforced at create/start only; BUY does not re-check
  `available`. Never compute spendable as `available − deployed`.
- **Portfolio max-loss baseline**: At Simulation start, freeze metric kind and
  value: **known-value equity** when `equityComplete` is true; otherwise
  **quote cash (USDT)**. For the session lifetime, loss = `baseline − current`
  under that frozen kind only. Never invent prices. If current cannot be
  computed under the frozen kind, reject new BUYs; do not declare the
  portfolio-loss stop from missing marks.
- Portfolio max-loss may be entered as an absolute USDT amount; a rate form,
  if offered, is a rate of that persisted baseline and is stored as both rate
  and derived amount (same pattern as session loss rates).
- **Deployed for an allocation binding**: For 010, deployed attributed to a
  bound session is the session’s open long USDT cost basis when long (aligned
  with Feature 009 `deployed` projection for that session); unbound sessions
  do not consume another allocation’s cap.
- Per-symbol weight uses Feature 009 known-value weights on **projected
  post-BUY** holdings; denominator is known-value Portfolio equity. USDT
  quote holding is not subject to the non-quote concentration cap. Stale
  marks follow Feature 002; missing/incomplete valuation rejects increasing
  exposure.
- New portfolio-aware Risk fields are optional in Settings; Simulation enforces
  required portfolio available check whenever allocated capital is set.
- Backtest and Strategy Comparison do not load live Portfolio gates in 010.
  They MUST continue to use the **same** shared Risk authority for session-
  style rules (optional profit/loss/max trades per Feature 004); portfolio-
  only context is absent/disabled — not a second engine.
- Reason catalog may add codes; existing codes keep their meaning for
  regression continuity. Codes are stable identifiers; messages are
  operator-facing text and MAY be clarified without renaming codes.
- UI stays under Auto Trading (configure/status/journals) + Settings defaults +
  Portfolio capital visibility; no new primary nav item.

## Non-Goals

- XT private authentication, sync, or Real XT Portfolio
- Real-money enablement or autonomous trading
- Second Risk engine for Backtest, Portfolio UI, Torque, or GE
- Daily / calendar loss limits
- Portfolio drawdown **stop** (report metric may remain on Backtest)
- Unifying session starting cash with Portfolio available into one wallet
- Execution abstraction redesign (Feature 011) beyond clarifying Risk boundaries
- Multi-exchange, leverage, shorts, margin
- Replacing Feature 008 Settings semantics
