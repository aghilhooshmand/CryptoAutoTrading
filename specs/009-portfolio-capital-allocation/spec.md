# Feature Specification: Portfolio & Capital Allocation Core

**Feature Branch**: `009-portfolio-capital-allocation`

**Created**: 2026-08-13

**Updated**: 2026-08-14 (Simulation Portfolio — locked product direction;
analyze remediation I1/U1/U2)

**Status**: DONE

Correction tasks T044–T087 are complete. Feature 009 is marked **DONE** on
`docs/ROADMAP.md`. Feature 010 remains PLANNED until started separately.

**Input**: User description: "Revise Feature 009 to a Simulation Portfolio that behaves like a normal crypto exchange portfolio. Operator may fund only simulation quote cash (primarily USDT). Do not provide UI or operator API to manually record BTC/ETH/SOL. Non-USDT holdings appear only when simulated executions create them (BUY decreases USDT and increases the asset; SELL reverses and updates realized P&L). Strategies never modify balances. Pipeline: Strategy → Controller → Risk → Execution → Portfolio/Accounting. Value with Feature 002 public prices; never invent prices. Keep capital reservation for future Risk/Torque but do not make it the dominant UI. Clear SIMULATION state; Feature 013 later adds a separate Real XT Portfolio. Persist snapshots on meaningful state changes; no fake history charts. Modern exchange-style UI per docs/UI_UX_STANDARDS.md."

## Clarifications

### Session 2026-08-14 (capital reservation — still in force except where superseded)

- Q: How should the operator establish initial quote cash? → A: Explicit Portfolio **funding** of simulation USDT. Funding must keep `quote_cash ≥ reserved`. Equity is the sum of valued holdings, not a synonym for cash.
- Q: What are deployed capital and the positions list? → A: First-class **read-model** fields, derived on GET from Feature 003. If one or more **active** sessions (`RUNNING` or `STOPPING`) have `position_side == long`, `positions` lists those open trades (session id, symbol/asset, side, quantity, cost basis when stored) and `deployed` is the sum of those sessions’ USDT `cost_basis`. Otherwise `deployed` is `"0"` and `positions` is `[]`. Holdings (balances) are distinct from positions (open trades). 009 does **not** attribute deployed USDT to a specific allocation; allocation resize/release is constrained only by FR-003 (`reserved ≤ quote_cash`). Per-allocation deployed limits belong to Feature 010.
- Q: How is available capital defined? → A: `available = quote_cash − reserved`. Quote cash is the USDT holding. Reserved cannot exceed quote cash. Deployed is reported separately and is not subtracted again from available in this feature’s reservation identity.
- Q: May two allocations share the same target label? → A: Yes — `targetRef` is a non-unique label.
- Q: Funding reduction below reserved? → A: Reject; resize/release allocations first; prior state unchanged.

### Session 2026-08-14 (holdings — **SUPERSEDED**)

The earlier decision that the operator may **manually record** BTC/ETH (or other) local/manual holdings is **void**. Non-quote holdings MUST NOT be operator-entered. They MUST appear only from simulated execution.

History/valuation clarifications from that session remain in force:

- Persist snapshots on meaningful portfolio/accounting changes only; no periodic price-only snapshots; 009 UI is current-state (no value-over-time or drawdown charts).
- Never invent prices. No usable price → unknown value, exclude from equity. Stale last-known → include with stale indicator. Any unvalued holding → equity labeled partial / known-value.

### Session 2026-08-14 (Simulation Portfolio — locked)

- Feature 009 is the **Simulation Portfolio** only. Operator-facing name: Simulation Portfolio. Not a bookkeeping sandbox.
- Operator may fund/add **simulation quote cash only** (primarily USDT). No normal UI (and no public operator API) to type in BTC, ETH, SOL, or other crypto quantities.
- Simulated BUY/SELL through the established pipeline **attempts** to update holdings (USDT and the traded asset, cost basis, realized P&L). Feature 003 session journals remain the session record even if the Simulation Portfolio refuses the apply.
- Feature 013 later adds a clearly separate **Real XT Portfolio** on the same domain with different provenance — not mixed into 009.
- Capital allocations remain in the model for future Risk/Torque but are a secondary, compact UI — not the dominant Portfolio experience.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect Simulation Portfolio (Priority: P1)

As an operator, I want a Simulation Portfolio page that shows total value,
available USDT, what I own, weights, and P&L so that it feels like a normal
exchange portfolio — not a manual ledger form.

**Why this priority**: This is the primary operator experience for Feature 009.

**Independent Test**: Fund 1000 USDT. Open Portfolio. Confirm SIMULATION is
obvious, total value equals USDT when that is the only holding, available USDT
is 1000, holdings show USDT only, and there is no form to add BTC/ETH/SOL.

**Acceptance Scenarios**:

1. **Given** the operator has not funded quote cash, **When** they open
   Portfolio, **Then** they can fund simulation USDT, and that amount appears
   as the USDT holding and as available cash (absent reservations).
2. **Given** only funded USDT, **When** they view Portfolio, **Then** they see
   summary cards (total value, available USDT, total P&L/return, realized and
   unrealized P&L), a holdings view with USDT, and empty or absent non-USDT
   rows — not invented BTC/ETH.
3. **Given** any Portfolio view, **When** they look for asset entry, **Then**
   there is no operator control to type a crypto quantity for BTC, ETH, SOL,
   or similar. Copy does not describe a “local/manual holdings book” or
   “not real-money brokerage funding” sandbox.
4. **Given** the page, **When** they check mode, **Then** Simulation is clearly
   indicated and the view is not labeled as a live XT account.

---

### User Story 2 - Holdings follow simulated execution (Priority: P1)

As an operator, I want BTC (and other traded assets) to appear automatically
when Simulation executes a BUY, and to decrease with USDT returning on SELL,
so that holdings come from the pipeline rather than from typing balances.

**Why this priority**: Without fill→portfolio accounting, the Simulation
Portfolio cannot show what was traded.

**Independent Test**: Fund 1000 USDT. Apply a simulated BUY of BTC that spends
200 USDT (test hook or live Simulation fill). Portfolio USDT decreases, BTC
quantity increases with cost basis from the fill. A later simulated SELL
reduces BTC, increases USDT, and updates realized P&L. Strategies are not
invoked as the writer of balances.

**Acceptance Scenarios**:

1. **Given** funded USDT and no BTC, **When** a simulated BUY BTC fill is
   applied through Execution → Portfolio/Accounting, **Then** USDT quantity
   decreases by the fill’s cash effect, BTC quantity increases, average cost
   is set from the fill, and provenance is simulation — not a live exchange.
2. **Given** a BTC holding from a prior simulated BUY, **When** a simulated
   SELL fill is applied, **Then** BTC quantity decreases (row removed if
   quantity reaches 0), USDT increases, and realized P&L updates. Unrealized
   P&L on remaining BTC uses public price vs remaining cost basis.
3. **Given** a strategy signal, **When** holdings change, **Then** the change
   is attributable to Controller → Risk → Execution → Portfolio/Accounting,
   never to strategy code writing balances.
4. **Given** Feature 003 session journals, **When** a fill is recorded on the
   session and then applied to the Simulation Portfolio, **Then** historical
   session/run journal rows are not rewritten. If portfolio apply is refused
   (insufficient USDT), journals stay as Feature 003 wrote them and Portfolio
   GET exposes `warning`. Backtest journals are not migrated onto this ledger
   in 009.

---

### User Story 3 - Capital reservation without dominating the UI (Priority: P2)

As an operator, I want quote-cash reservations to remain available for future
Risk and Torque, without the Portfolio page being an allocation-first form.

**Why this priority**: Constitution requires explicit allocations; the locked
UX requires they stay secondary.

**Independent Test**: With known available USDT C, create two valid
allocations summing to ≤ C, reject overspend, release/resize, and confirm
holdings quantities are unchanged. The primary page still leads with summary
and holdings; allocations sit in a compact or expandable Capital section.

**Acceptance Scenarios**:

1. **Given** available quote cash C, **When** the operator creates allocations
   summing to ≤ C, **Then** reserved and available update (`available =
   cash − reserved`) and holdings (including any BTC from fills) are not
   copied into per-strategy wallets.
2. **Given** an overspend or a funding cut below reserved, **When** they
   submit, **Then** the change is rejected and prior state is unchanged.
3. **Given** the Portfolio layout, **When** they scan the page, **Then**
   summary and holdings are primary; Available / Reserved / Deployed appear
   as compact capital figures; allocation CRUD is not the visual center.

---

### User Story 4 - Persist Simulation Portfolio state (Priority: P1)

As an operator, I want funded USDT, fill-driven holdings, and reservations to
survive reload.

**Why this priority**: A non-persisted portfolio cannot be inspected after
restart.

**Independent Test**: Fund USDT, apply a simulated BUY, create an allocation,
reload. Same quantities and reservations remain (prices may refresh).

**Acceptance Scenarios**:

1. **Given** funded USDT, fill-created holdings, and allocations, **When** the
   operator reloads, **Then** quantities, cost basis, provenance, capital
   categories, and allocation records remain inspectable.
2. **Given** a rejected invalid mutation, **When** they reload, **Then** the
   last valid state is still present.

---

### User Story 5 - Current-state value, weights, and P&L (Priority: P2)

As an operator, I want honest current valuation, weights, and P&L — including
a simple current allocation visual — without invented history.

**Why this priority**: Exchange-style scanning needs totals and weights; fake
charts would violate evidence rules.

**Independent Test**: With USDT plus a valued BTC holding, confirm total
value, weights (visual and numeric), and P&L. Missing price → quantity
visible, value unknown, equity partial. No value-over-time or drawdown chart.

**Acceptance Scenarios**:

1. **Given** valued holdings, **When** the operator views Portfolio, **Then**
   they can read total value, available USDT, per-asset weight (including a
   simple donut or equivalent current-state visual), and P&L/return when
   defined. USDT does not show an artificial unrealized P&L.
2. **Given** snapshots persisted on funding, fills, and allocation changes,
   **When** they view Portfolio, **Then** they do not see value-over-time,
   P&L-over-time, or drawdown presented as facts.
3. **Given** a missing or stale public price, **When** that holding is shown,
   **Then** quantity remains; missing price → value unknown (not zero);
   stale last-known → included and marked stale; incomplete books labeled
   partial / known-value.

---

### Edge Cases

- Allocation size ≤ 0 → rejected; prior state unchanged.
- Reserved would exceed quote cash → rejected.
- Funding would make quote cash < reserved → rejected.
- Reduce allocation while a session has open deployed exposure → allowed in
  009 if FR-003 still holds (`reserved ≤ quote_cash`). Do not invent
  per-allocation deployed in this feature.
- Repeated submit of the same allocation change → must not double-reserve.
- No simulated trades yet → holdings show USDT after funding only; do not
  invent BTC/ETH/SOL rows.
- Simulated BUY with insufficient Simulation Portfolio USDT to apply the
  fill’s cash effect → do not invent negative USDT; do **not** roll back the
  Feature 003 session fill/journals; persist a fill-apply warning; GET
  `/portfolio` returns that text in `warning` until a later successful
  `apply_simulation_fill`. Corrupt-state `warning` takes precedence if both
  exist.
- Simulated SELL whose quantity exceeds the Simulation Portfolio holding for
  that asset → do not invent a short or negative quantity; do **not** mutate
  holdings; do **not** roll back Feature 003 journals; persist a fill-apply
  warning (same path as insufficient USDT); GET `/portfolio` exposes
  `warning` until a later successful `apply_simulation_fill`.
- Holding quantity that would reach 0 after SELL → remove the asset row.
- Missing public price → quantity visible; value/weight/unrealized unknown;
  exclude from equity; do not treat value as zero.
- Stale last-known public price → include value; mark stale.
- Any unvalued holding → equity labeled partial / known-value.
- Unknown cost basis → do not invent average price or unrealized P&L.
- Corrupt stored state → fail closed; do not invent balances or prices.
- Simulation Portfolio MUST NOT be presented as a live XT account.
- Operator MUST NOT be able to PUT/DELETE non-USDT holdings via the
  Portfolio UI or public operator API.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide one authoritative **Simulation
  Portfolio** accounting model: holdings, total value (equity), quote cash
  (USDT holding), available, reserved, deployed, realized/unrealized/total
  P&L, allocations, and positions. Not a separate “capital book” vs “asset
  book.” `deployed` and `positions` MUST be derived on read from active
  Feature 003 sessions with a long position (see Clarifications). They MUST
  NOT be a second operator-editable ledger.
- **FR-001a**: The operator MUST fund simulation quote cash (USDT) through
  explicit Portfolio funding. Feature 008 Settings MUST NOT become the
  portfolio ledger. Funding MUST preserve `quote_cash ≥ reserved`. Funding
  MUST NOT mean “set equity” once other valued holdings exist.
- **FR-001b**: Each holding MUST store asset, quantity, and cost basis when
  known. Inspection MUST show public price, USDT value, and weight when a
  usable price exists. When cost basis and value exist, show unrealized P&L
  and return. USDT MUST NOT be given an artificial unrealized P&L. Unknown
  cost or value → omit P&L/return — do not fabricate.
- **FR-001c**: The operator MUST NOT record, adjust, or delete non-quote
  holdings through a normal Portfolio UI or public operator holdings API.
  Non-USDT holdings MUST be created/updated only when simulated execution
  applies a fill: BUY decreases USDT and increases the asset (cost basis
  from the fill); SELL decreases the asset, increases USDT, and updates
  realized P&L. Fill apply MUST move USDT by the Feature 003 fill
  `cash_delta` (net of that fill’s fees/slippage as Feature 003 computed
  them). Holding `realizedPnl` on SELL MUST use
  `(fill_price − average_cost) × qty` when average cost is known and MUST
  NOT invent a second fee line — fee drag appears in quote cash / equity via
  `cash_delta`. A SELL that would reduce quantity below zero MUST be refused
  the same way as an insufficient-USDT apply (no book mutation; journals
  unchanged; warning). Feature 009 MUST NOT place real-money or XT private
  orders.
- **FR-001d**: Total value MUST be the sum of valued holding market values.
  P&L figures MUST be coherent with holdings (no double count with
  allocations). Unvalued holdings → equity labeled partial / known-value.
- **FR-001e**: Feature 009 provenance is **simulation**. The UI MUST label
  Simulation Portfolio and MUST NOT present it as a live XT account.
  Feature 009 MUST NOT call XT private APIs. Feature 013 later introduces a
  separate Real XT Portfolio on the same holdings domain (`exchange`
  provenance).
- **FR-002**: Explicit quote-cash allocations MUST exist for named uses
  without transferring ownership to strategy logic. `targetRef` MAY be
  shared across allocations.
- **FR-003**: `available = quote_cash − reserved`, `reserved ≤ quote_cash`,
  both ≥ 0. Reservations MUST NOT change non-USDT quantities. Double
  reservation of the same quote cash MUST be prevented. Cross-allocation
  spend MUST be preventable by this identity.
- **FR-004**: Strategies MUST remain advisory. They MUST NEVER write
  holdings, balances, allocations, or P&L. Trading that affects the
  Simulation Portfolio MUST follow Strategy → Controller → Risk →
  Execution → Portfolio/Accounting.
- **FR-005**: Each allocation has a stable id and reserved size and is a
  child of the Simulation Portfolio — not a second portfolio.
- **FR-006**: The operator MAY create, inspect, resize, and release
  allocations subject to FR-003. The Portfolio UI MUST treat this as a
  compact/advanced Capital section, not the primary layout.
- **FR-007**: Persist holdings quantities, cost basis, provenance,
  funding, and allocations across restart. Prices MAY refresh on read.
- **FR-007a**: Persist snapshots on meaningful **successful** book changes:
  funding, simulation fill-driven holding mutations, allocation create/resize/
  release. MUST NOT snapshot on GET, price ticks, or refused fill-apply. MUST NOT show
  value-over-time, P&L-over-time, or drawdown in 009 UI. A **current-state**
  allocation visual (donut or equivalent of present weights) is allowed.
- **FR-008**: Invalid funding, allocation, or fill-apply updates MUST be
  rejected with a clear reason and MUST leave last valid **portfolio** state
  unchanged. A refused fill-apply MUST NOT roll back Feature 003 session
  journals already written for that fill.
- **FR-009**: Feature 003/004 session and run journals MUST remain
  compatible (regression suites stay green). 009 MUST NOT rewrite historical
  journals. After a successful Feature 003 fill (session journals already
  recorded), 009 MUST **attempt** `apply_simulation_fill` in the same DB
  session. If apply would invent negative USDT, the Simulation Portfolio
  book MUST stay unchanged (no `simulation_fill` snapshot), the hook MUST
  catch/refuse without aborting the session transaction, and GET MUST expose
  `warning` (fill-apply text, unless a corrupt-state warning supersedes).
  Backtest fill ledgers are not migrated in 009.
- **FR-010**: Portfolio UI under the existing primary Portfolio area:
  summary cards, current allocation visual, holdings table (cards on narrow
  viewports). Inherit `docs/UI_UX_STANDARDS.md`. Avoid large explanatory
  paragraphs, developer jargon, and manual crypto-entry forms.
- **FR-011**: Clear labels and units (asset quantity vs USDT value).
  Simulation MUST be distinguishable from any future real-money view. This
  feature MUST NOT enable real-money trading.
- **FR-011a**: Value non-USDT holdings with Feature 002 public `{asset}_usdt`
  quotes. Never invent prices. No usable price → unknown value, not zero;
  exclude from equity. Stale last-known (Feature 002 60s rule) → include
  and mark stale. Any unvalued holding → partial equity. Weights are shares
  of known-value equity.
- **FR-012**: MUST NOT implement XT private auth/sync, real-money execution,
  leverage, shorts, margin, multi-exchange portfolios, auto-rebalancing,
  Torque/GE, autonomous trading, or strategy ranking.

### Key Entities

- **Simulation Portfolio**: The operator-visible 009 accounting container.
- **Holding**: Asset balance (USDT = quote cash; other assets from sim fills).
- **Allocation**: Quote-cash reservation; child of the portfolio.
- **Position**: Open simulated pipeline exposure; distinct from holdings.
- **Snapshot**: Persisted on meaningful mutations; not shown as history UI.
- **Provenance**: `simulation` in 009; `exchange` reserved for Feature 013.

## Success Criteria *(mandatory)*

- **SC-001**: Within one minute on Portfolio, an operator can read total
  value, available USDT, holdings (asset, quantity, value when known),
  weights, and P&L without opening strategy screens, and can see that this
  is Simulation — not a live XT account.
- **SC-002**: Automated tests prove valid allocations summing to ≤ available
  USDT succeed and over-reservation is rejected with prior state unchanged.
- **SC-003**: After fund + simulated BUY + allocation + reload, quantities
  and reservations remain inspectable.
- **SC-004**: Automated checks prove `available = quote_cash − reserved`,
  equity = sum of valued holdings, allocations are not added into equity,
  and partial equity is marked when any holding is unvalued.
- **SC-005**: Simulation and Backtest regression suites stay green.
- **SC-006**: Primary inspect + fund (+ compact allocate) remain usable
  around 375px; holdings use cards if a table is too dense; help is not
  hover-only.
- **SC-007**: With at least two valued holdings, the operator can read
  approximate weights from the page (numeric and/or donut) without doing
  the math by hand.
- **SC-008**: Missing price or cost does not produce fabricated value, P&L,
  or return. Stale prices are marked. Partial equity is labeled.
- **SC-009**: Automated tests prove a simulated BUY/SELL updates USDT and
  the traded asset when portfolio USDT can absorb the cash effect; that a
  refused apply leaves journals intact and GET `warning` set; and that no
  public operator endpoint accepts a manual BTC (or similar) holdings upsert.

## Assumptions

- One Simulation Portfolio per local operator machine in v1.
- Quote currency is USDT-oriented.
- Feature 003 session journals remain the session run record; 009 **attempts**
  fill→portfolio accounting for **new** Simulation fills. Session starting
  capital on Auto Trading is not silently overwritten from Settings.
  Unifying session starting cash with Portfolio available is allowed later
  but is not Feature 010. When those ledgers diverge, Portfolio GET `warning`
  is the operator-visible signal; the missed fill is not invented later.
- Backtest stays on its own run ledger in 009.
- Allocations reserve USDT only.
- Long-only / no leverage in 009 holdings semantics.
- Existing Portfolio nav; no new top-level item.
- Donut (or equivalent) visualizes **current** weights only.

## Non-Goals

- Operator UI or public API to type BTC/ETH/SOL (or other) quantities
- XT private authentication, sync, or Real XT Portfolio (Feature 013)
- Real-money enablement
- Leverage, shorts, margin, multi-exchange books
- Auto-rebalancing / optimization
- Torque / GE
- Autonomous trading
- Replacing Feature 008 Settings
- Rewriting historical Simulation/Backtest journals
- Value-over-time or drawdown charts in 009
- Periodic price-only snapshots
- Feature 010 Advanced Risk Management
