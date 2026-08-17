# Feature Specification: XT Account / Private API Integration

**Feature Branch**: `013-xt-account-private-api`

**Created**: 2026-08-16

**Status**: Clarified (session 2026-08-16). **DONE (XT private read as-built).**
**Amendment 2026-08-17 — venue-neutral private-account + Kraken implementation:
IN PROGRESS.** Feature 002 Kraken public (identity + public adapter) is
complete; this amendment is the next living delivery. No Real orders in 013.

**Input**: Feature 013 — Private XT account integration (primarily read-only). Establish authenticated private-exchange connectivity for real XT account balances, open orders, and order status, with credential configuration that fails closed, normalized private errors, basic rate-limit handling, and an explicit Real XT account representation that never merges with Simulation Portfolio. Locked out: operator Real trading mode, Strategy→XT orders, RealExecutionAdapter live fills, **all place/cancel capability** (unconditionally deferred to Feature 015+), autonomous trading, withdrawals/transfers, Features 014–015 hardening/confirmed execution. Architecture lock: strategies never call XT; future path remains Strategy → Controller → Risk → RealExecutionAdapter → XT Private Client, but RealExecutionAdapter remains unavailable for live trading in this feature.

## Amendment 2026-08-17 — Kraken-first private read

Living direction for Feature 013 (same feature id; do not create 026; do not
rename `XtAccountService` to a Kraken class as the architecture).

**Locks:**

1. Venue-neutral private-account **port** (balances, open orders, order
   lookup) with **Kraken as the first implementation**.
2. Feature 013 remains **read-only**. No place/cancel. No Real Kraken orders.
3. Credentials: environment/secrets only (`KRAKEN_API_KEY` /
   `KRAKEN_API_SECRET` or equivalent documented names). Never hard-code or
   commit secrets. Fail closed if missing/invalid.
4. Kraken signing/payloads stay inside the Kraken private adapter.
5. Provenance `venue = kraken`. Simulation Portfolio never written or merged.
6. Keep XT private code/UI temporarily for regression; not the live
   destination. Stop new XT development.
7. Coinbase out. Depends on Feature **002** Kraken public (product identity).
8. Strategy, Controller, Risk MUST NOT import Kraken private types.
9. RealExecutionAdapter MUST remain unavailable for live fills in 013.
10. Operator UI: **Real Account / Venue: Kraken**; no trading buttons.
    Prefer available/held in product assets over “XT Portfolio” / “USDT-only
    real account”.

Original FR-001–FR-017 describe the XT as-built. **Living amendment
requirements are FR-018–FR-030.** Where they conflict, FR-018–FR-030 win.

- **FR-018**: Feature 013 MUST expose a venue-neutral private-account boundary
  (balances, open orders, order status) that core and UI consume without
  Kraken or XT types.
- **FR-019**: The first implementation of that boundary MUST be a **Kraken**
  private adapter. Do not implement Coinbase. Do not treat a renamed XT
  service as the architecture.
- **FR-020**: Kraken private authentication/signing MUST remain inside the
  Kraken adapter. Core MUST NOT construct Kraken signatures.
- **FR-021**: Credentials MUST load from environment/secrets only; fail closed
  with `credentials_missing` / `authentication_failed` (same meanings as
  XT as-built). Placeholders only in `.env.example`.
- **FR-022**: The system MUST read Kraken balances and map available/free vs
  held/locked **only where Kraken actually provides that split**; MUST NOT
  invent locked amounts. Omit zero/zero after normalization.
- **FR-023**: The system MUST list open orders and look up order status on
  Kraken, normalized to venue-neutral order identity (`venue_order_id`,
  `venue_product_id`).
- **FR-024**: Private errors MUST be normalized to stable codes (at least
  credentials_missing, authentication_failed, timestamp_invalid, rate_limited,
  venue_private_unavailable, order_not_found). XT-specific code names MAY
  remain as legacy aliases on the XT adapter only.
- **FR-025**: Rate-limit handling MUST remain bounded (at most one automatic
  retry; honor Retry-After within a bound or short backoff).
- **FR-026**: Account data MUST carry `venue = kraken` provenance and MUST NOT
  write or merge into Feature 009 Simulation Portfolio.
- **FR-027**: Minimal read-only Real Account UI (Venue: Kraken) MUST exist;
  MUST NOT accept secrets or expose place/cancel/Real trading controls.
  Legacy `/portfolio/real-xt` MAY remain until replaced.
- **FR-028**: Public Feature 002 (including Kraken public) MUST remain usable
  without private credentials.
- **FR-029**: Feature 013 MUST NOT enable RealExecutionAdapter live fills or
  any order placement/cancel. Deferred to Feature 015 after this Kraken read
  path is complete.
- **FR-030**: Implement this amendment only after Feature 002 Kraken public
  market data (identity + public adapter) is complete. Automated tests MUST
  cover Kraken signing fixtures (no live keys), fail-closed credentials,
  normalize, isolation, and absence of trading controls.

### Amendment success criteria

- **SC-009**: No credentials → 100% Kraken account reads fail closed.
- **SC-010**: Fixtures retrieve Kraken balances/orders with `venue=kraken`
  without mutating Simulation Portfolio.
- **SC-011**: Inspect UI has no trading controls.
- **SC-012**: RealExecutionAdapter still places no exchange order from 013.
- **SC-013**: Strategy/Controller/Risk have no Kraken private imports.

### Amendment out of scope

Place/cancel, Real trading mode, withdrawals/transfers, Coinbase, XT live
trading, autonomous trading, Feature 015 execution.

---

## Clarifications

### Session 2026-08-16

- Q: Should Feature 013 include a read-only operator UI to inspect Real XT balances and orders, or only backend/service access with no new UI screen? → A: Minimal read-only inspect UI for balances, open orders, and order status; clearly separate from Simulation Portfolio; no trading actions (Option B).
- Q: Should place-order and cancel-order stay completely out of Feature 013? → A: Unconditionally out of scope; defer all place/cancel capability to Feature 015+ (Option A).
- Q: How should Feature 013 handle XT private rate-limit responses on safe read-only GETs? → A: Maximum one automatic retry; honor Retry-After within a bounded wait, otherwise short backoff, then return `rate_limited` (Option A).
- Q: How should Feature 013 treat signing failures from clock skew / invalid timestamp window? → A: Distinct stable code `timestamp_invalid` with clock-skew/timestamp message; fail closed; return no account data; never auto-adjust the system clock (Option B).
- Q: When normalizing Real XT balances, how should assets with zero free and zero locked be treated? → A: Omit zero/zero balances; keep any asset with non-zero free or locked; a valid account with none is a successful empty list (Option A).

## Behavior locks (non-negotiable)

1. **Private account / read-first MVP only** — no live trading product path in Feature 013.
2. **Private client is separate** from Feature 002 public market-data client.
3. **Credentials** come from environment/secrets only; never hard-coded or committed; missing/invalid credentials **fail closed**.
3a. **Timestamp / clock-skew signing failures** fail closed as `timestamp_invalid` (no invented account data; never auto-adjust the system clock).
4. **No withdrawal** capability is required or used; keys are expected to be read-scoped (or least privilege without withdrawal).
5. **Simulation Portfolio (Feature 009) is never written** from XT balances and never merged with Real XT account data.
6. **RealExecutionAdapter** (Feature 012) remains **unavailable for live trading** in this feature (structured unavailable outcome for trading fills).
7. **Strategies, Controller, and Risk** are not bypassed; strategies must not call the exchange.
8. **Place-order / cancel-order** are **unconditionally out of scope** for Feature 013 (product workflows, operator actions, and private-client place/cancel capability); deferred entirely to Feature 015+.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure private credentials safely (Priority: P1)

As an operator, I want to supply XT private API credentials outside source code so the platform can authenticate for account reads without embedding secrets.

**Why this priority**: Without fail-closed credential handling, account integration is unsafe or silently broken.

**Independent Test**: With credentials absent → account reads fail closed with a clear credentials-missing style outcome; with invalid credentials → authentication-failed style outcome; secrets never appear in repository files or ordinary logs.

**Acceptance Scenarios**:

1. **Given** no private credentials are configured, **When** an operator requests Real XT account data, **Then** the system fails closed with a stable credentials-missing outcome and does not invent balances or orders.
2. **Given** credentials are configured but rejected by the exchange, **When** an account read is attempted, **Then** the system returns an authentication-failed style outcome and does not expose partial fabricated account state as authoritative.
3. **Given** credentials are present in the configured secret location, **When** the operator reviews project source and ordinary configuration examples, **Then** no real secret values are committed or hard-coded.

---

### User Story 2 - View Real XT balances with clear provenance (Priority: P1)

As an operator, I want to see my real XT spot account balances (asset, free/available, locked, and total when available), labeled as real XT account data, separate from Simulation Portfolio.

**Why this priority**: Account visibility is the core value of Feature 013 and the prerequisite for later controlled real trading.

**Independent Test**: With valid read credentials (or a recorded exchange fixture), retrieve a balance list that includes free/locked (and total when derivable) and an explicit real-XT provenance marker; Simulation Portfolio holdings remain unchanged.

**Acceptance Scenarios**:

1. **Given** valid private credentials, **When** the operator requests Real XT balances, **Then** each balance entry identifies the asset and free/available and locked amounts, with total when the exchange data allows derivation, and assets with both free and locked zero are omitted.
2. **Given** Real XT balances are shown, **When** the operator inspects Simulation Portfolio, **Then** Simulation Portfolio values are unchanged and are not mixed into the Real XT account view.
3. **Given** Real XT account data is presented in the inspect UI, **When** the operator reads provenance/labeling and nearby Simulation Portfolio surfaces, **Then** Real XT data is unambiguous and not mixed with simulation capital, and no trading actions are available on the Real XT inspect surface.
4. **Given** a valid account whose balances are all zero/zero after normalization, **When** balances are retrieved, **Then** the outcome is a successful empty list (not an error).

---

### User Story 3 - Inspect open orders and order status (Priority: P1)

As an operator, I want to list open orders on the real XT account and look up an order’s status so I can verify account activity without placing trades from this product.

**Why this priority**: Completes read-side account awareness needed before any future order placement feature.

**Independent Test**: Retrieve open-order list and a single-order status for a known order id (live or fixture); missing order yields order-not-found style outcome.

**Acceptance Scenarios**:

1. **Given** valid credentials and open orders on the account (or fixture), **When** the operator requests open orders, **Then** each order includes enough identity and state to distinguish it (symbol/side/quantity/status fields as available from the exchange).
2. **Given** a known order identifier, **When** the operator requests order status, **Then** the system returns a normalized status view or an order-not-found style outcome if the exchange has no such order.
3. **Given** Feature 013 is active, **When** the operator uses only Feature 013 account capabilities, **Then** no place-order or cancel-order workflow is offered as a product path.

---

### User Story 4 - Understand private failures and rate limits (Priority: P2)

As an operator, I want private XT failures and rate limits to surface as stable codes and readable messages so I can distinguish missing credentials, auth failure, timestamp/clock issues, rate limiting, and temporary unavailability.

**Why this priority**: Fail-closed behavior is only operable if errors are diagnosable and retries do not hammer the exchange.

**Independent Test**: Simulate or fixture credentials_missing, authentication_failed, timestamp_invalid, rate_limited, xt_private_unavailable, and order_not_found; confirm at most one automatic retry on rate limits (Retry-After within bound or short backoff), then `rate_limited` with no uncontrolled loops.

**Acceptance Scenarios**:

1. **Given** a private call fails for a known reason class, **When** the operator sees the outcome, **Then** a stable machine-readable code from the Feature 013 set is present along with an operator-readable message.
2. **Given** the exchange signals rate limiting on a read-only GET, **When** the system handles the response, **Then** it performs at most one automatic retry after honoring `Retry-After` within a bounded wait (or a short backoff if `Retry-After` is absent/unusable), and if still rate-limited returns `rate_limited` with no further automatic retries.
3. **Given** the private service is temporarily unreachable, **When** a read is attempted, **Then** the outcome is an unavailable-style failure—not invented empty balances presented as success.
4. **Given** the exchange rejects a signed request for timestamp/clock-window reasons, **When** the system maps the failure, **Then** it returns `timestamp_invalid` with a clock-skew/timestamp-oriented message, returns no account data, and does not auto-adjust the system clock.

---

### User Story 5 - Keep trading pipeline closed for real fills (Priority: P1)

As a platform maintainer, I want RealExecutionAdapter to remain unavailable for live trading and strategies still unable to call XT, so Feature 013 cannot accidentally enable real orders.

**Why this priority**: Safety lock against premature real-money execution.

**Independent Test**: Attempt a Real execution fill path → unavailable outcome; Strategy modules still have no direct private XT access; Simulation trading paths unchanged.

**Acceptance Scenarios**:

1. **Given** Feature 013 is implemented, **When** RealExecutionAdapter is asked to execute a trading fill, **Then** it remains unavailable for live trading (no exchange order is placed).
2. **Given** a strategy evaluation runs, **When** inspecting strategy and controller boundaries, **Then** strategies still do not call XT private or public trading endpoints directly.
3. **Given** ordinary Simulation create/run flows, **When** Feature 013 is present, **Then** those flows require no Real trading mode selection and continue to use Simulation execution.

---

### Edge Cases

- Missing credentials → fail closed (`credentials_missing`); no invented account snapshot.
- Invalid/expired credentials → fail closed (`authentication_failed`).
- Timestamp / clock-skew signing rejection → fail closed (`timestamp_invalid`) with clock-skew/timestamp message; no account data; never auto-adjust system clock.
- Rate limited → at most one automatic retry (Retry-After within bound or short backoff), then `rate_limited`; no uncontrolled loops.
- Exchange timeout / malformed response → `xt_private_unavailable` (or equivalent unavailable code); fail closed.
- Order id unknown → `order_not_found`.
- Empty balances / no open orders → successful empty lists, not errors.
- Assets with both free and locked normalized to zero → omit from the balance list; retain any asset with non-zero free or locked.
- Partial exchange payloads → normalize what is trustworthy; do not invent locked/free fields.
- Concurrent Simulation Portfolio use → Real XT reads never mutate Simulation Portfolio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a private XT authenticated client capability, separate from the Feature 002 public market-data client, using operator-configured API key and secret with signed private requests.
- **FR-002**: Credentials MUST be supplied via environment/secrets configuration only; the system MUST NOT hard-code or commit credential values.
- **FR-003**: When credentials are missing or invalid for a private operation, the system MUST fail closed with stable codes `credentials_missing` or `authentication_failed` respectively (or equivalent documented aliases that map to these meanings).
- **FR-004**: Private credentials used by Feature 013 MUST NOT require withdrawal permissions; the product MUST NOT invoke withdrawal or transfer operations.
- **FR-005**: The system MUST retrieve Real XT account balances with asset identity, free/available amount, locked amount, and total when derivable from exchange data. Assets whose free/available and locked amounts are both zero (after normalization) MUST be omitted; any asset with non-zero free or locked MUST be retained; an account with no remaining assets MUST be represented as a successful empty balance list (not an error).
- **FR-006**: Real XT account data MUST carry explicit real-XT provenance and MUST be presented as distinct from Simulation Portfolio.
- **FR-007**: The system MUST NOT write XT balances into Feature 009 Simulation Portfolio and MUST NOT merge Simulation and XT balances into one authoritative book.
- **FR-008**: The system MUST list open orders for the authenticated Real XT account in a normalized form suitable for operator inspection.
- **FR-009**: The system MUST look up order status by order identity and return a normalized status or `order_not_found` when absent.
- **FR-010**: Private XT failures MUST be normalized to stable machine-readable codes including at least: `credentials_missing`, `authentication_failed`, `timestamp_invalid`, `rate_limited`, `xt_private_unavailable`, `order_not_found`, plus operator-readable messages.
- **FR-010a**: When the exchange rejects a signed private request due to timestamp window / clock-skew validation, the system MUST fail closed with `timestamp_invalid`, include a clock-skew/timestamp-oriented operator message when detectable, MUST return no account data for that request, and MUST NOT auto-adjust the host system clock.
- **FR-011**: On rate-limit responses for safe read-only private GETs, the system MUST perform **at most one** automatic retry: honor `Retry-After` when present and within a documented bounded wait, otherwise use a short fixed backoff; if the retry is still rate-limited (or wait would exceed the bound), MUST return `rate_limited` and MUST NOT retry further or run uncontrolled loops.
- **FR-012**: Feature 013 MUST expose a **minimal read-only operator inspect UI** for Real XT balances, open orders, and order-status lookup, clearly labeled with real-XT provenance and visually/structurally separate from Simulation Portfolio, with **no** trading actions (no place/cancel, no Real trading mode). Backend/service access supporting that UI MUST also exist for tests and operators.
- **FR-012a**: The inspect UI MUST NOT accept, display, or transmit private API secrets; credentials remain environment/secrets only (never frontend-configured).
- **FR-013**: Strategies MUST NOT call XT directly; Controller and Risk remain between any future trading intent and execution.
- **FR-014**: RealExecutionAdapter MUST remain unavailable for live trading fills in Feature 013 (no exchange order placement via that adapter).
- **FR-015**: Place-order and cancel-order MUST remain **unconditionally out of scope** for Feature 013—no product workflows, no operator actions, and no private-client place/cancel capability. All place/cancel is deferred to Feature 015+.
- **FR-016**: Public market-data behavior (Feature 002) MUST remain available without private credentials.
- **FR-017**: Automated tests MUST cover: signed request construction/auth headers, missing-credentials fail-closed, timestamp_invalid / clock-skew fail-closed (no clock mutation), balance normalization, open-order normalization, order-status normalization, private error normalization, rate-limit behavior, Simulation Portfolio isolation, and absence of an exposed real order-execution product path.

### Key Entities

- **Private credentials**: Operator-supplied API key and secret for XT private access (never stored in source).
- **Real XT account balance**: Asset, free/available, locked, optional total; provenance = real XT.
- **Real XT open order**: Exchange order identity plus normalized trading fields/status for open orders.
- **Order status view**: Lookup result for a single order identity.
- **Private error outcome**: Stable code + operator-readable message for private-path failures.
- **Simulation Portfolio**: Feature 009 local simulation capital book — isolated from Real XT account data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With credentials intentionally removed, 100% of Real XT account read attempts fail closed with a credentials-missing style outcome (no invented balances/orders).
- **SC-002**: With valid credentials (or equivalent fixtures), an operator can retrieve Real XT balances showing free/available and locked amounts for at least one asset when the account holds that asset, via the minimal read-only inspect UI (or its supporting service used by that UI).
- **SC-003**: An operator can retrieve an open-order list and an order-status lookup outcome from the read-only inspect UI without any place/cancel trading control present on that surface.
- **SC-004**: In a controlled check, completing Real XT account reads leaves Simulation Portfolio reserved/available/holdings unchanged.
- **SC-005**: Attempting RealExecutionAdapter trading execution in this feature never places an exchange order.
- **SC-006**: Ordinary Simulation create/run requires no new Real trading mode configuration to keep prior behavior.
- **SC-007**: Private failure fixtures map to the required stable codes (`credentials_missing`, `authentication_failed`, `timestamp_invalid`, `rate_limited`, `xt_private_unavailable`, `order_not_found`) in automated checks.
- **SC-008**: Rate-limit handling tests demonstrate at most one automatic retry (Retry-After within bound or short backoff), then `rate_limited`, with no uncontrolled looping.

## Assumptions

- Feature 012 is on `main`; RealExecutionAdapter stub remains the live-trading gate (unavailable).
- XT private access uses signed requests with API key + secret; plan phase will bind to XT’s current private balance and order-query capabilities requiring **read** (not withdrawal) permissions.
- Spot account reads are the MVP surface; futures/derivatives private account surfaces are deferred unless trivially shared.
- “Total” balance is shown when free+locked (or exchange-provided total) is available; otherwise free and locked alone are acceptable.
- Zero/zero balances are omitted after normalization; non-zero free or locked assets are kept; none remaining → successful empty list.
- Operator visibility is a **minimal read-only inspect UI** (balances, open orders, order status) with explicit Real XT provenance, separate from Simulation Portfolio, and no trading actions; credentials stay env/secrets-only (never in the UI).
- Place/cancel are unconditionally out of scope for Feature 013 (including private-client capability); deferred entirely to Feature 015+. Account read visibility does not require place/cancel.
- Rate-limit policy for safe private GETs: max one automatic retry; honor `Retry-After` within a bounded wait, else short backoff; then return `rate_limited`.
- Timestamp/clock-skew signing rejections map to `timestamp_invalid`; fail closed with no account data; never auto-adjust the system clock.
- Public Feature 002 client stays unsigned and credential-free.

## Out of Scope

- Operator-selectable Real trading mode
- Strategy → XT order execution
- RealExecutionAdapter live fills / order placement
- Place-order or cancel-order in any form (product workflows, operator actions, private-client place/cancel APIs)—unconditionally deferred to Feature 015+
- Autonomous trading
- Withdrawals and transfers
- Crash/restart hardening (Feature 014)
- Confirmed real-money execution UX (Feature 015)
- Merging XT balances into Simulation Portfolio
- Changing Dual EMA or Risk rule catalogs
- Requiring withdrawal-capable API keys

## Planning notes (non-normative; for `/speckit-plan`)

These items are identified for planning and are **not** stakeholder FRs:

1. **Endpoints (to confirm against current XT private docs in plan)**: authenticated balance query; open-orders query; order status/lookup by id — separate host/client from public `sapi` market GETs used in Feature 002.
2. **Signing/auth**: HMAC-based request signing with key/secret and required validation headers/timestamp window per XT private docs; map window/skew rejections to `timestamp_invalid` (FR-010a).
3. **Domain models**: Real XT balance, open order, order status entities with real-XT provenance.
4. **Error/rate-limit contract**: codes listed in FR-010 (including `timestamp_invalid`); 429 handling per FR-011 (max one retry; Retry-After within bound or short backoff).
5. **Credential design**: environment/secrets variables; fail closed; document placeholders only in examples.
6. **API/UI**: read-only account snapshot/open-orders/status; no trading mode.
7. **Tests**: FR-017 list.
8. **Defer to 015+**: all place/cancel capability (client methods, RealExecutionAdapter live fills, confirmed real execution UX).
9. **Bounded wait for Retry-After**: plan should pick a concrete max wait (e.g. a few seconds) so operator UX stays responsive.

---

## Amendment 2026-08-17 — Kraken private-read implementation plan

**Implement after Feature 002 Kraken public is complete.**

Add a Kraken private adapter behind a venue-neutral private-account port.
Keep `backend/app/xt_account/` for regression. Do not rename it to Kraken.
Do not add place/cancel. Do not wire RealExecutionAdapter writes.

- Kraken private REST signing per current Kraken docs (verify at implement;
  do not copy XT `validate-*` headers).
- Env: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`.
- Map balances / open orders / order lookup to venue-neutral DTOs with
  `venue=kraken`.
- Free vs locked: only fields Kraken actually returns; never invent.
- UI: Real Account, Venue: Kraken; no order buttons.
- Tests: recorded signing vectors; fail closed; Portfolio isolation.
