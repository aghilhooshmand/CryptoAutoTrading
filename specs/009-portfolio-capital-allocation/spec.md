# Feature Specification: Portfolio & Capital Allocation Core

**Feature Branch**: `009-portfolio-capital-allocation`

**Created**: 2026-08-13

**Updated**: 2026-08-14 (holdings/accounting reconcile)

**Status**: Draft

**Input**: User description: "Portfolio & Capital Allocation Core — Build one coherent portfolio/accounting foundation for CryptoAutoTrading, in the spirit of an exchange account view plus explicit capital reservation. Track what assets the operator owns (quantity, market price, market value, weight, cost basis where known, realized/unrealized P&L, return per holding) and the portfolio totals (equity, quote cash, available, reserved, deployed, total P&L/return). Support explicit capital allocations so quote cash can later be assigned safely to strategies, trading programs, or Torque branches without over-allocation, double reservation, negative available capital, or spending another allocation’s reserved cash. Holdings, balances, allocations, and P&L are independent from strategy logic. Strategies remain advisory and must never directly modify holdings, balances, allocations, or P&L. All trading continues Strategy → Controller → Risk → Execution → Portfolio/Accounting. Use existing public market data to value supported holdings in the quote currency (primarily USDT) where possible. Design holdings so later Simulation, real-exchange sync, and Torque can reuse the same domain without a second portfolio implementation. Persist effective state for inspection and reproducibility. Provide a practical operator-facing Portfolio page following docs/UI_UX_STANDARDS.md. Do not implement XT private/account integration, real-money execution, leverage, short selling, margin, automatic rebalancing/optimization, Torque grammar, or Grammatical Evolution."

## Clarifications

### Session 2026-08-14 (capital reservation — still in force except where superseded below)

- Q: How should the operator establish the local portfolio’s initial cash / equity in Feature 009? → A: Operator explicitly sets starting **quote cash** (USDT-oriented) via a controlled Portfolio funding action; later quote-cash adjustments use the same controlled funding path and must keep capital invariants. **Superseded in part (2026-08-14 holdings reconcile):** funding sets quote-currency cash/holdings, not total portfolio equity. Equity is the sum of holding market values.
- Q: In Feature 009, before Simulation/Real Money are bound to allocations, what should “capital deployed in positions” and the positions list represent? → A: First-class portfolio fields that remain zero/empty in 009 until a later feature binds trading activity; still shown clearly so the capital model is complete. **Still in force for positions/deployed.** Holdings are a distinct first-class concept (asset balances) and are not the same as the positions list.
- Q: How should available capital be defined relative to cash, allocated/reserved capital, and deployed capital? → A: `available = cash − reserved`; deployed is a distinct reported category (0 in 009); reserved cannot exceed cash. **Still in force** with cash meaning **quote-currency cash** (the USDT holding), not total equity.
- Q: May two different allocations both reference the same strategy or program label at the same time? → A: Yes — multiple allocations may share the same optional target reference if capital invariants hold; targets are labels, not unique ownership keys.
- Q: When the operator reduces portfolio cash through a funding adjustment, what must happen if the new cash would be below total reserved capital? → A: Reject the reduction; require release/resize of allocations first; leave prior state unchanged.

### Session 2026-08-14 (holdings / exchange-style portfolio)

Pending `/speckit-clarify`. Informed defaults are recorded under Assumptions; open decisions are marked `[NEEDS CLARIFICATION]` in requirements.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect exchange-style holdings and portfolio value (Priority: P1)

As a local operator, I want a Portfolio view that shows what I own—each asset,
quantity, current market price when known, current value, weight in the
portfolio, cost basis / average acquisition price where known, realized P&L,
unrealized P&L, and return—plus total portfolio equity and total P&L/return,
so that Portfolio feels like an account/holdings page rather than a hidden
internal ledger.

**Why this priority**: Without holdings and a single equity figure, capital
reservation has nothing coherent to sit on, and later Simulation / real-money /
Torque work would invent a second “asset portfolio.”

**Independent Test**: Establish known holdings (at least quote cash; other
assets if this feature’s write path includes them), open Portfolio, and confirm
each holding’s quantity and known valuation fields, portfolio totals, and that
weights sum to 100% among holdings whose values are known (within ordinary
rounding).

**Acceptance Scenarios**:

1. **Given** the operator has not yet funded quote cash, **When** they open
   Portfolio, **Then** they can set explicit starting quote cash via a
   controlled funding action, and that cash appears as the quote-currency
   holding (not as a separate unrelated “capital book”).
2. **Given** the portfolio has quote cash and zero other assets, **When** the
   operator opens Portfolio, **Then** they see total equity equal to that quote
   cash (when the quote asset is valued 1:1), available/reserved/deployed
   capital categories, realized and unrealized P&L, an empty or clearly empty
   positions list, and a holdings list that at least shows the quote asset.
3. **Given** the portfolio holds more than one asset with known market values
   (for example USDT, BTC, ETH), **When** the operator views Portfolio,
   **Then** they see each asset’s quantity, current price when available,
   current value in quote currency, and weight as a share of total equity, and
   they can identify total equity as the sum of those values without opening
   strategy screens.
4. **Given** cost basis is known for a holding, **When** the operator views
   that holding, **Then** they see average acquisition price (or equivalent
   cost basis), unrealized P&L vs current value, and a simple return for that
   holding. **Given** cost basis is unknown, **Then** quantity is still shown
   and P&L/return for that holding is shown as unknown—not invented.
5. **Given** any displayed snapshot, **When** the operator checks provenance,
   **Then** the view does not present local/manual or simulated balances as a
   live exchange account.

---

### User Story 2 - Create and manage explicit capital allocations (Priority: P1)

As a local operator, I want to create, adjust, and release explicit capital
allocations against **available quote cash** (for example 500 USDT with 250
reserved for program A, 150 for program B, and 100 remaining available) so that
unused quote cash stays available and no allocation can overspend or spend
cash reserved for another allocation.

**Why this priority**: Explicit allocations remain constitutionally required
for multi-strategy and future Torque branches; holdings do not replace them.

**Independent Test**: From a portfolio with known available quote cash C,
create two valid allocations that sum to ≤ C, attempt an overspending
allocation and confirm rejection, then release or reduce an allocation and
confirm available quote cash increases accordingly.

**Acceptance Scenarios**:

1. **Given** available quote cash of C, **When** the operator creates one
   allocation of size C for a single target label, **Then** the allocation is
   accepted, available quote cash becomes 0, and reserved equals C (absent
   deployment).
2. **Given** available quote cash of C, **When** the operator creates multiple
   allocations whose sizes sum to ≤ C, **Then** each allocation is recorded
   independently with its own identity and size, unused remainder stays
   available, and the portfolio still shows one shared equity base (holdings
   are not copied into per-strategy wallets).
3. **Given** available quote cash of C, **When** the operator attempts an
   allocation that would make total reserved exceed quote cash, **Then** the
   system rejects the change with a clear reason and leaves the prior
   portfolio/allocation/holdings state unchanged.
4. **Given** an existing allocation that is not fully deployed, **When** the
   operator reduces or releases it within allowed rules, **Then** reserved
   decreases and available quote cash increases by the released amount without
   creating negative available capital.
5. **Given** any allocation create/resize/release attempt, **When** validation
   fails (over-allocation, invalid size, inconsistent state), **Then** no
   partial corrupt update is persisted.
6. **Given** quote cash reserved for allocation A, **When** a later spending
   path (including future execution binding) would spend that reserved cash
   for a different allocation, **Then** that spend is rejected; Feature 009
   must make this ownership rule part of the accounting model even if 009
   itself does not yet execute trades.

---

### User Story 3 - Inspect allocation-level accounting within one portfolio (Priority: P2)

As a local operator, I want each allocation to show its own reserved size and
a simple accounting summary while still belonging to the same portfolio so
that I can compare how quote cash was assigned without treating allocations as
separate portfolios or strategy-owned wallets.

**Why this priority**: Independent allocation records are required for future
concurrent programs; they must not fork holdings or double-count equity.

**Independent Test**: Create at least two allocations with different sizes,
inspect each allocation’s reserved capital and summary, and confirm portfolio
holdings/equity still reconcile as one book.

**Acceptance Scenarios**:

1. **Given** two allocations A and B under one portfolio, **When** the
   operator inspects each, **Then** each shows its own identity, reserved
   quote cash, and allocation-level fields provided by this feature (at
   minimum reserved size; performance fields when activity exists).
2. **Given** those allocations, **When** the operator returns to holdings and
   totals, **Then** portfolio equity and holdings remain the single source of
   truth and allocation figures do not double-count equity.
3. **Given** an allocation with no trading activity yet, **When** the
   operator inspects it, **Then** reserved quote cash and membership in the
   parent portfolio remain obvious.

---

### User Story 4 - Persist portfolio, holdings, and allocations (Priority: P1)

As a local operator, I want portfolio holdings, quote-cash funding, and
allocation state persisted so that after restart I can inspect the same
effective picture and later features can reuse this domain.

**Why this priority**: A non-persisted book cannot support reproducibility or
later Simulation / real-money / Torque binding.

**Independent Test**: Establish quote cash (and any other holdings this
feature allows), create allocations, reload, and confirm the same holdings,
capital categories, and allocation records remain inspectable.

**Acceptance Scenarios**:

1. **Given** the operator has established holdings and one or more
   allocations, **When** they reload the application, **Then** Portfolio shows
   the same effective holdings quantities, capital categories, and allocation
   records (market prices may refresh; quantities and reservations must not
   silently disappear).
2. **Given** a rejected invalid allocation or funding change, **When** the
   operator reloads, **Then** the last valid persisted state is still present.

---

### User Story 5 - Understand simple current-state portfolio analytics (Priority: P2)

As a local operator, I want only those portfolio analytics that current data
can support correctly—total value, weights, realized/unrealized P&L, total
P&L/return, and per-holding performance where cost basis exists—so that I am
not shown invented history or false precision.

**Why this priority**: Useful, honest numbers beat a professional-looking
terminal that fabricates drawdown or time series.

**Independent Test**: With known holdings and known vs unknown cost basis,
confirm totals and per-holding P&L match the stated identities; confirm no
historical chart or drawdown figure appears unless historical state actually
exists.

**Acceptance Scenarios**:

1. **Given** holdings with known values, **When** the operator views
   Portfolio, **Then** they can read total equity, each holding’s weight, and
   portfolio realized, unrealized, and total P&L/return when those figures are
   defined.
2. **Given** Feature 009 does not yet have sufficient historical snapshots,
   **When** the operator views Portfolio, **Then** they do not see
   value-over-time, P&L-over-time, or maximum-drawdown figures presented as
   calculated facts.
3. **Given** public market data for a supported holding is missing or not
   current, **When** that holding is valued, **Then** the operator sees a
   clear unavailable or stale treatment and the system does not invent a
   price to complete the books.

---

### Edge Cases

- Allocation size of zero or negative → rejected; prior state unchanged.
- Sum of allocation reserves would exceed quote cash → rejected with a clear
  over-allocation reason.
- Funding reduction that would make quote cash below total reserved →
  rejected; operator must release/resize allocations first; prior state
  unchanged.
- Reducing an allocation below capital already deployed for that allocation
  (when deployment exists) → rejected or constrained so accounting stays
  consistent.
- Concurrent or repeated submit of the same allocation change → must not
  double-apply reservations.
- Empty positions list when no pipeline positions exist → shown as no open
  positions, not as missing data. In Feature 009 this remains the normal
  positions state until later binding.
- Empty non-quote holdings → do not invent BTC/ETH rows the operator does
  not own; show quote cash holding after funding.
- Holding quantity of zero → not presented as an owned asset.
- Missing or stale public price for a holding → do not invent a price;
  quantity remains visible; value/weight/unrealized P&L follow the chosen
  fail-closed valuation rule.
- Unknown cost basis → do not invent average price or unrealized P&L.
- Corrupt or inconsistent stored portfolio/holdings/allocation state on load
  → fail closed with a clear operator warning; do not invent balances,
  quantities, or P&L to “fix” the books.
- Simulated or local/manual holdings must never be labeled as a live
  exchange account.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide one authoritative local portfolio
  accounting model (not a separate “capital portfolio” and “asset
  portfolio”) that includes: holdings, total equity, quote cash, available
  quote capital, reserved quote capital, deployed capital, realized P&L,
  unrealized P&L, allocations, and positions. Quote cash MUST be the
  quote-currency holding (USDT-oriented), not a parallel cash ledger.
- **FR-001a**: The operator MUST establish and adjust quote cash through
  explicit controlled Portfolio funding actions. Feature 008 Settings MUST
  NOT silently become the portfolio ledger. Funding MUST preserve capital
  invariants. A funding reduction that would make `quote cash < reserved`
  MUST be rejected with a clear reason; prior valid state MUST remain
  unchanged. Funding MUST NOT treat “set equity” as a synonym for “set
  quote cash” once non-quote holdings exist.
- **FR-001b**: Each holding MUST record at least: asset identity, quantity,
  and enough information to later store cost basis / average acquisition
  price when known. On inspection, when public market data can value that
  asset in the quote currency, the system MUST present current price,
  current market value, and weight of that holding in total equity. When
  cost basis is known, it MUST also present unrealized P&L and a simple
  return for that holding. When cost basis is unknown, P&L/return for that
  holding MUST be omitted or marked unknown—not fabricated.
- **FR-001c**: How non-quote holdings (for example BTC or ETH) first appear
  in Feature 009 itself is [NEEDS CLARIFICATION: 009 write path for
  non-quote holdings — quote-cash funding only until later execution
  binding; operator local/manual bootstrap of quantities and optional cost
  basis; or another allowed origin]. The model MUST still define holdings so
  later execution can apply: quote cash decreases, the bought asset
  quantity increases, cost basis updates, then market value and unrealized
  P&L change with price, then a sell decreases the asset, increases quote
  cash, and updates realized P&L. Feature 009 MUST NOT itself place
  real-money or XT private orders to create that lifecycle.
- **FR-001d**: Total equity MUST be the sum of holding market values in the
  quote currency for holdings that are included under the valuation rule.
  Equity MUST NOT be defined as quote cash alone once other valued holdings
  exist. Portfolio realized P&L, unrealized P&L, and total P&L/return MUST
  be coherent with holding-level figures (no double counting).
- **FR-001e**: Holdings MUST carry a provenance/source distinction sufficient
  for later mapping (at least: local/manual or bootstrap if used;
  simulation; real-exchange synchronization). Feature 009 MUST NOT call XT
  private/account APIs. Feature 012 remains responsible for XT private
  integration. The 009 model MUST be reusable so Feature 012 can map
  exchange balances into this same holdings/accounting domain rather than
  a second portfolio implementation. A simulated or local balance MUST NOT
  be presented as a real XT balance.
- **FR-002**: The system MUST support explicit capital allocations that
  reserve **quote cash** for named uses (strategy, trading program, Torque
  branch, or operator label) without transferring ownership of capital or
  holdings to strategy logic. An optional target reference MUST NOT be
  required to be unique across allocations; multiple allocations MAY share
  the same target reference when total reserved still respects FR-003.
- **FR-003**: Capital identity for Feature 009 MUST be:
  `available = quote_cash − reserved`, with `reserved ≥ 0`, `available ≥ 0`,
  and `reserved ≤ quote_cash`. Quote cash is the spendable quote-currency
  holding. Reserved MUST NOT be subtracted from non-quote asset quantities.
  Deployed capital is a distinct reported category (pipeline capital in
  open positions) and MUST NOT be subtracted again from available in this
  feature’s undeployed foundation (deployed remains 0 until later binding).
  Double reservation of the same quote cash MUST be prevented. Spending
  quote cash reserved for another allocation MUST be preventable by the
  model (no silent cross-allocation spend).
- **FR-004**: Strategies MUST remain advisory only. Strategy logic MUST
  NEVER directly create, invent, or modify holdings, balances, allocations,
  reservations, positions, or P&L. Any future trading that uses portfolio
  capital MUST continue Strategy → Controller → Risk → Execution →
  Portfolio/Accounting.
- **FR-005**: Each allocation MUST have a stable identity and reserved quote
  size, and MUST remain a child of the parent portfolio (not a separate
  portfolio and not a copy of holdings). Identity is the allocation record
  itself, not the optional target reference.
- **FR-006**: The system MUST allow the operator to create, inspect, adjust
  (resize), and release allocations subject to FR-003.
- **FR-007**: The system MUST persist the effective portfolio, holdings
  quantities, cost basis when known, provenance, and allocation state needed
  for inspection after restart. Market prices MAY be refreshed on read from
  public market data and need not be the persisted source of truth.
- **FR-007a**: Historical portfolio snapshots (value over time, P&L over
  time, maximum drawdown, best/worst holdings over a history) are
  [NEEDS CLARIFICATION: persist historical snapshots in 009 vs current
  effective state only, with time-series analytics deferred until enough
  history exists]. Feature 009 MUST NOT present historical analytics as
  facts if it does not yet have sufficient historical state to calculate
  them correctly.
- **FR-008**: Invalid allocation, funding, or holdings updates MUST be
  rejected with a clear reason and MUST leave the last valid persisted
  state unchanged.
- **FR-009**: Existing Simulation and Backtest session/run accounting MUST
  remain compatible: historical effective configurations and results MUST
  NOT be rewritten by introducing the portfolio model. Full migration of
  Simulation/Backtest fill ledgers onto the portfolio ledger is out of
  scope for this feature. Later features bind execution into this domain.
- **FR-010**: The operator MUST have a Portfolio-facing UI under the
  existing primary Portfolio area that presents holdings and capital
  reservation in a simple, practical, exchange-style layout (not a
  professional portfolio-management terminal). General form/feedback/
  responsive rules inherit from `docs/UI_UX_STANDARDS.md` and constitution
  XIV.
- **FR-011**: Amounts MUST have clear labels and units (asset quantity vs
  quote value). Simulation, local/manual, and any future real-money context
  MUST remain distinguishable. This feature MUST NOT enable real-money
  trading.
- **FR-011a**: Supported holdings SHOULD be valued using existing public
  market data (Feature 002) in the quote currency (primarily USDT) when a
  matching public price exists. Missing or stale prices MUST NOT be
  invented. Exact treatment of missing vs stale prices when computing
  equity and weights is [NEEDS CLARIFICATION: exclude unvalued holdings
  from equity; include last-known price with a stale warning; or mark
  whole-portfolio equity unavailable if any included holding cannot be
  valued safely].
- **FR-012**: This feature MUST NOT implement: XT private/account
  authentication or synchronization; real-money execution; leverage; short
  selling; margin; multi-exchange portfolios; automatic portfolio
  rebalancing or optimization; Torque grammar/program execution;
  Grammatical Evolution; autonomous trading; or strategy ranking.

### Key Entities

- **Portfolio**: The single local accounting container. Owns holdings,
  allocations, capital categories, provenance, and derived totals. Not a
  strategy wallet.
- **Holding**: An asset balance in the portfolio (asset, quantity, cost
  basis when known, provenance). Market price, market value, weight,
  unrealized P&L, and return are inspection fields derived from quantity,
  cost basis, and public market data when available. The quote-currency
  holding **is** quote cash.
- **Allocation**: An explicit reservation of quote cash for a named future
  use. Child of the portfolio; does not own holdings.
- **Position (pipeline view)**: Open trading exposure produced through
  Controller → Risk → Execution. Distinct from holdings. Empty/zero
  deployed in Feature 009 until later binding.
- **Capital / portfolio snapshot**: Operator-visible coherent view of
  holdings + capital categories + allocations at a point in time.
  Historical snapshot persistence is subject to FR-007a.
- **Allocation Target Reference**: Optional non-authoritative label
  (strategy id or program name). Not a unique ownership key; does not
  execute trades.
- **Provenance**: Source of a balance or portfolio book (local/manual,
  simulation, real-exchange). Display must not collapse these together.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can open Portfolio and, within one minute,
  identify holdings (asset, quantity, value when known), total equity,
  quote cash, available, reserved, deployed, realized P&L, unrealized P&L,
  and positions without consulting strategy screens.
- **SC-002**: In a portfolio with known available quote cash C, the
  operator can create a valid split of allocations summing to ≤ C, and
  every attempt to reserve more than allowed is rejected with no change to
  prior state (verified in automated tests).
- **SC-003**: After establishing holdings and allocations and reloading,
  100% of last valid quantities, capital categories, and allocation records
  remain inspectable (no silent loss of reserved cash or holdings).
- **SC-004**: Automated checks prove `available = quote_cash − reserved`,
  available never goes negative, reserved never exceeds quote cash,
  double-reservation cannot succeed, and (when all included holdings are
  valued) equity equals the sum of those holding values without
  double-counting allocations into equity.
- **SC-005**: Existing Simulation and Backtest regression suites that encode
  current session/run accounting remain green after this feature lands.
- **SC-006**: Portfolio primary workflows for inspect holdings + allocate
  remain usable around 375px width, with clear units/labels and
  non-hover-only help where terms are non-obvious.
- **SC-007**: Given at least two valued holdings, an operator can state
  each asset’s approximate weight of the portfolio (for example 50% / 30% /
  15% / 5%) from the Portfolio page without calculating by hand.
- **SC-008**: When cost basis is unknown or a public price is missing, the
  operator is not shown a fabricated P&L, return, or market value for that
  gap.

## Assumptions

- **Single local portfolio for v1**: One operator machine, one
  authoritative local portfolio (no multi-user or multi-portfolio product).
- **Quote currency**: USDT-oriented, matching existing public market data
  (USDT-quoted pairs) and Simulation/Backtest money presentation. Roadmap
  “€500” examples remain illustrative of split scenarios, not a second
  fiat ledger.
- **One book**: Quote cash, holdings, equity, reservations, and P&L are
  views of one accounting model. USDT quantity is quote cash; BTC/ETH are
  other holdings; equity is the quote-valued sum of holdings.
- **Reservation vs inventory**: Allocations reserve spendable quote cash.
  They do not reserve BTC/ETH units and do not create per-strategy
  sub-wallets of holdings.
- **Holdings vs positions**: Holdings = balances. Positions = pipeline
  open trades. Feature 009 shows positions as empty and deployed as 0
  until later binding. A BTC balance is a holding even when there is no
  open pipeline position.
- **Funding vs equity**: Controlled funding changes quote cash (and thus
  the quote holding). It does not overwrite crypto holdings or set equity
  independently of valuation.
- **No execution in 009**: Creating/resizing allocations does not trade.
  The buy/sell lifecycle is the domain contract for later Simulation /
  Execution / Feature 012 binding, not an XT private call in this feature.
- **Valuation source**: Public market data already available for supported
  USDT-quoted pairs. Quote asset (USDT) values 1:1 in quote currency.
  Unsupported assets are not silently given fake prices.
- **Analytics honesty**: Current-state totals, weights, and P&L where
  inputs exist. No fabricated drawdown or equity curve.
- **Settings remain defaults**: Feature 008 does not own the portfolio
  ledger.
- **Simulation session cash stays session-local** until a later binding
  feature maps fills into this domain (FR-009).
- **Long-only / no leverage in v1 constraints**: No short, margin, or
  leveraged holding semantics.
- **Primary navigation**: Existing Portfolio area; no new top-level nav.
- **UI**: Simple exchange-style holdings + allocation panel; inherit
  `docs/UI_UX_STANDARDS.md`.
- **Dependencies**: Application shell, public market data, constitution
  capital protection / advisory strategies / portfolio authority
  (especially I, II, III–IV, VIII, XIII–XIV, XXXIII–XXXIV). Feature 012
  will later map private exchange balances into this same domain.

## Non-Goals

- XT private account authentication, sync, or live exchange balance import
- Real-money enablement or execution
- Leverage, short selling, margin, multi-exchange portfolios
- Automatic portfolio rebalancing or optimization
- Torque grammar/runtime and Grammatical Evolution
- Autonomous trading
- Replacing Feature 008 Settings
- Full rewrite of historical Simulation/Backtest journals onto this ledger
  in this feature
- A second, separate asset-portfolio product beside capital reservation
- Presenting simulated or local/manual balances as a real XT account
- Inventing historical performance charts when no historical book exists
