# Tasks: XT Account / Private API Integration

**Input**: Design documents from `/specs/013-xt-account-private-api/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required — FR-017 / SC-001–SC-008 (signing, credentials fail-closed,
`timestamp_invalid`, balance/order normalization, error codes, rate-limit
bounds, Portfolio isolation, no real order-execution product path,
RealExecutionAdapter still unavailable, FR-016 public market without private
creds, FR-004 no withdraw/transfer). Prefer mocks/`httpx.MockTransport`;
no live XT in CI.

**Analyze remediations** (2026-08-16): G1 FR-016 task T053; G2 FR-004 docs +
client/router/tests; I1 ROADMAP MVP vs deferred; I2 `credentials_missing` →
HTTP 503; U1 create `features/xt-account/` in T025; plus G3 clock-mutation in
T035 and U2 UI standards in T051.

**Organization**: New `backend/app/xt_account/` package + `/xt-account/*` API +
`/portfolio/real-xt` inspect UI. Propose commits only; do not auto-commit.
Keep Feature 013 `DONE` on `docs/ROADMAP.md` after acceptance gates (T052).

**Spec locks** (must hold through all tasks):
- Private read-only MVP; **no** place/cancel methods, routes, or UI actions (FR-015)
- Private client separate from Feature 002 `XtSpotAdapter` (FR-001, FR-016)
- Credentials env-only (`XT_API_KEY` / `XT_API_SECRET`); never frontend (FR-002, FR-012a)
- Fail closed: `credentials_missing`, `authentication_failed`, `timestamp_invalid`,
  `rate_limited`, `xt_private_unavailable`, `order_not_found` (FR-010 / FR-010a)
- Rate limit: max **one** retry; Retry-After capped at **3s**, else **0.5s** backoff (FR-011 / research R4)
- Omit zero/zero balances; empty list = success (FR-005)
- Never write/merge Simulation Portfolio (FR-006, FR-007)
- RealExecutionAdapter remains `real_execution_unavailable` (FR-014)
- Strategies must not call XT private trading APIs (FR-013)
- UI under Portfolio sub-route; no 4th primary nav (constitution XIII)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US5 map to spec stories

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/013-xt-account-private-api/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

**Purpose**: Package skeleton and credential documentation placeholders

- [x] T001 Create `backend/app/xt_account/` package skeleton (`__init__.py`, empty modules per `plan.md`: `credentials.py`, `signing.py`, `errors.py`, `models.py`, `client.py`, `normalize.py`, `service.py`)
- [x] T002 [P] Document `XT_API_KEY` / `XT_API_SECRET` placeholders only (no real secrets) in project `.env.example` and/or `README.md`; state keys MUST be read-scoped (no withdrawal permission required) per FR-004 / constitution XVIII / `research.md` R5

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Shared private-client infrastructure used by all account-read stories

**⚠️ CRITICAL**: No user-story endpoints/UI until this phase completes

- [x] T003 Implement stable private error types/codes in `backend/app/xt_account/errors.py` (`credentials_missing`, `authentication_failed`, `timestamp_invalid`, `rate_limited`, `xt_private_unavailable`, `order_not_found`) per `contracts/xt-private-signing.md`
- [x] T004 Implement env credential loader in `backend/app/xt_account/credentials.py` (`XT_API_KEY`, `XT_API_SECRET`); missing/blank → `credentials_missing` before any network call
- [x] T005 Implement XT v4 HMAC-SHA256 header signing in `backend/app/xt_account/signing.py` per `contracts/xt-private-signing.md` / research R3 (default `validate-recvwindow` = `5000`)
- [x] T006 [P] Implement domain models in `backend/app/xt_account/models.py` (`RealXtBalance`, open-order / order-status views, snapshot fields, `bookProvenance` / `provenance` = `real_xt`) per `data-model.md`
- [x] T007 Implement injectable `XtPrivateClient` signed GET transport in `backend/app/xt_account/client.py` (`httpx.AsyncClient`, base `https://sapi.xt.com`, timeout aligned with public adapter patterns) — **read helpers only**; no place/cancel; **no** withdraw/transfer methods (FR-004, FR-015)
- [x] T008 Implement `XtAccountService` orchestration shell in `backend/app/xt_account/service.py` (credential gate + client injection + error mapping hook points)
- [x] T009 Add FastAPI router stub `backend/app/api/xt_account.py` and register it in `backend/app/main.py` under `/xt-account` (no place/cancel or withdraw/transfer routes)
- [x] T010 [P] Export public symbols from `backend/app/xt_account/__init__.py`
- [x] T011 [P] Add unit tests in `backend/tests/unit/test_xt_account_signing.py` for deterministic signature fixtures (fixed timestamp/key/path/query)
- [x] T012 [P] Add unit tests in `backend/tests/unit/test_xt_account_credentials.py` for missing/blank env → `credentials_missing`

**Checkpoint**: Signing + credentials + models + client/service shells exist; no business read endpoints required yet

---

## Phase 3: User Story 1 - Configure private credentials safely (Priority: P1) 🎯 MVP

**Goal**: Operators supply XT private credentials via env; account reads fail closed when missing/invalid; secrets never appear in source or ordinary API responses.

**Independent Test**: Unset credentials → `/xt-account/*` returns `credentials_missing` with HTTP **503** and no invented balances/orders; invalid-auth fixture → `authentication_failed`; public `/market/*` still works without private env; no secret values in repo examples or error bodies.

### Tests

- [x] T013 [P] [US1] Contract tests in `backend/tests/contract/test_xt_account_api.py` asserting missing credentials on planned routes return HTTP **503** + stable `credentials_missing` error envelope (no fabricated account payload) per `contracts/xt-account-api.md`
- [x] T053 [P] [US1] Assert Feature 002 public market paths remain usable without private credentials in `backend/tests/contract/test_market_data.py` and/or a thin case in `backend/tests/contract/test_xt_account_api.py` (unset `XT_API_KEY`/`XT_API_SECRET`; FR-016)

### Implementation

- [x] T014 [US1] Wire credential fail-closed across `XtAccountService` entrypoints in `backend/app/xt_account/service.py` so every private read checks credentials first
- [x] T015 [US1] Map XT auth failures (`AUTH_101`/`102`/`103`/`104`/`106` and related) to `authentication_failed` in `backend/app/xt_account/errors.py` / service mapping (exclude timestamp cases handled in US4)
- [x] T016 [US1] Ensure API error responses in `backend/app/api/xt_account.py` never include API key/secret material; keep operator-readable messages only; map `credentials_missing` → HTTP 503
- [x] T017 [US1] Run US1 gates until green: `backend/tests/unit/test_xt_account_credentials.py`, `backend/tests/unit/test_xt_account_signing.py`, credentials + FR-016 cases in `backend/tests/contract/test_xt_account_api.py` / `backend/tests/contract/test_market_data.py`

**Checkpoint**: MVP credential safety — fail closed without secrets leakage

---

## Phase 4: User Story 2 - View Real XT balances with clear provenance (Priority: P1)

**Goal**: Retrieve and display Real XT balances (asset, free, locked, total when derivable) with `real_xt` provenance, separate from Simulation Portfolio; omit zero/zero rows.

**Independent Test**: Fixture balances normalize correctly (zero/zero omitted; empty list success); `GET /xt-account/balances` returns `bookProvenance: real_xt`; Portfolio snapshot unchanged; inspect UI shows Real XT balances without trading actions.

### Tests

- [x] T018 [P] [US2] Unit tests in `backend/tests/unit/test_xt_account_normalize.py` for balance mapping (`availableAmount`/`frozenAmount`/`totalAmount`) and zero/zero omission
- [x] T019 [P] [US2] Contract tests in `backend/tests/contract/test_xt_account_api.py` for `GET /xt-account/balances` success/empty/error shapes per `contracts/xt-account-api.md`
- [x] T020 [P] [US2] Isolation test in `backend/tests/unit/test_xt_account_portfolio_isolation.py` asserting Simulation Portfolio reserved/available/holdings unchanged after xt-account balance reads

### Implementation

- [x] T021 [US2] Implement balance normalization in `backend/app/xt_account/normalize.py` (omit zero/zero; decimal strings; provenance `real_xt`)
- [x] T022 [US2] Implement `get_balances()` on `XtPrivateClient` → XT `GET /v4/balances` in `backend/app/xt_account/client.py`
- [x] T023 [US2] Implement balances orchestration in `backend/app/xt_account/service.py` and `GET /xt-account/balances` in `backend/app/api/xt_account.py`
- [x] T024 [US2] Add frontend API client `frontend/src/services/xtAccountApi.ts` for balances (no credential fields)
- [x] T025 [US2] Create `frontend/src/features/xt-account/` (e.g. balances panel component) and `frontend/src/pages/RealXtAccountPage.tsx` composing it with Real XT labeling/badge, refresh, empty/loading/error states; **no** trading controls; register route `/portfolio/real-xt` in `frontend/src/App.tsx`
- [x] T026 [US2] Add navigation link from Simulation Portfolio page `frontend/src/pages/PortfolioPage.tsx` to Real XT inspect without merging data models/`portfolioApi`
- [x] T027 [US2] Run US2 gates until green: `backend/tests/unit/test_xt_account_normalize.py`, balances cases in `backend/tests/contract/test_xt_account_api.py`, `backend/tests/unit/test_xt_account_portfolio_isolation.py`

**Checkpoint**: Balances readable via API + inspect UI; Portfolio isolated

---

## Phase 5: User Story 3 - Inspect open orders and order status (Priority: P1)

**Goal**: List open orders and look up order status by id; missing order → `order_not_found`; no place/cancel product path.

**Independent Test**: Fixture open-order list and single-order status normalize; `GET /xt-account/open-orders` and `GET /xt-account/orders/{orderId}` match contract; unknown id → `order_not_found`; UI has lookup + list, no cancel/place.

### Tests

- [x] T028 [P] [US3] Extend `backend/tests/unit/test_xt_account_normalize.py` for open-order and order-status field mapping
- [x] T029 [P] [US3] Extend `backend/tests/contract/test_xt_account_api.py` for open-orders + order-status success/empty/`order_not_found` per contract

### Implementation

- [x] T030 [US3] Implement order normalizers in `backend/app/xt_account/normalize.py`
- [x] T031 [US3] Implement `list_open_orders(symbol?)` and `get_order(order_id)` on `XtPrivateClient` → XT `GET /v4/open-order` and `GET /v4/order/{orderId}` in `backend/app/xt_account/client.py` (still **no** place/cancel)
- [x] T032 [US3] Implement service methods + `GET /xt-account/open-orders` and `GET /xt-account/orders/{orderId}` in `backend/app/api/xt_account.py`; map XT `ORDER_005` → `order_not_found`
- [x] T033 [US3] Extend `frontend/src/services/xtAccountApi.ts` and `RealXtAccountPage` / `frontend/src/features/xt-account/` panels for open orders list + order-id lookup (read-only)
- [x] T034 [US3] Run US3 gates until green: order cases in `backend/tests/unit/test_xt_account_normalize.py` and `backend/tests/contract/test_xt_account_api.py`; confirm no place/cancel routes under `/xt-account` in `backend/app/api/xt_account.py`

**Checkpoint**: Full read-side account inspect (balances + orders) without trading actions

---

## Phase 6: User Story 4 - Understand private failures and rate limits (Priority: P2)

**Goal**: Stable codes for private failures including `timestamp_invalid`; rate-limit handling max one retry with bounded wait; no invented success payloads.

**Independent Test**: Fixtures map to all FR-010 codes; `AUTH_105`/skew → `timestamp_invalid` with skew-oriented message and no account data; 429 → ≤1 retry then `rate_limited`; UI surfaces code + message.

### Tests

- [x] T035 [P] [US4] Unit tests in `backend/tests/unit/test_xt_account_errors_rate_limit.py` covering XT `mc` → stable code map (incl. `timestamp_invalid`), Retry-After ≤3s / short 0.5s backoff / skip retry when wait would exceed bound, max-one-retry, and **no system-clock mutation** (assert set-time APIs not invoked) per FR-010a / FR-017
- [x] T036 [P] [US4] Extend `backend/tests/contract/test_xt_account_api.py` proving error envelopes for `authentication_failed`, `timestamp_invalid`, `rate_limited`, `xt_private_unavailable`, `order_not_found` (and `credentials_missing` → HTTP 503)

### Implementation

- [x] T037 [US4] Complete XT envelope/`mc`/HTTP mapping in `backend/app/xt_account/errors.py` (and client/service call sites) per `contracts/xt-private-signing.md`; never auto-adjust system clock
- [x] T038 [US4] Implement rate-limit policy in `backend/app/xt_account/service.py` or `client.py` (max one retry; `MAX_RETRY_AFTER_WAIT_S=3.0`; `SHORT_BACKOFF_S=0.5`) per research R4 / FR-011
- [x] T039 [US4] Surface stable `error.code` + message on Real XT inspect UI (`frontend/src/pages/RealXtAccountPage.tsx` / feature panels) using existing alert patterns
- [x] T040 [US4] Run US4 gates until green: `backend/tests/unit/test_xt_account_errors_rate_limit.py` and related cases in `backend/tests/contract/test_xt_account_api.py`

**Checkpoint**: Operator-diagnosable private failures with bounded rate-limit behavior

---

## Phase 7: User Story 5 - Keep trading pipeline closed for real fills (Priority: P1)

**Goal**: RealExecutionAdapter stays unavailable; strategies still cannot call XT for trading; Simulation flows need no Real trading mode; Feature 013 adds no place/cancel capability.

**Independent Test**: `RealExecutionAdapter.execute` → `real_execution_unavailable`; no `/xt-account` place/cancel/withdraw/transfer routes; Simulation create/run unchanged; client has no fund-movement methods.

### Tests

- [x] T041 [P] [US5] Keep/extend `backend/tests/unit/test_real_execution_stub.py` asserting `real_execution_unavailable` and no exchange order placement
- [x] T042 [P] [US5] Add assertions in `backend/tests/contract/test_xt_account_api.py` (or `backend/tests/unit/test_xt_account_no_fund_movement.py`) that place/cancel **and** withdraw/transfer routes/methods are absent on router + `XtPrivateClient` (FR-004, FR-015)
- [x] T043 [P] [US5] Smoke ordinary Simulation create/run needs no Real trading mode via existing tests under `backend/tests/contract/` / `backend/tests/integration/` (no intentional expectation edits)

### Implementation

- [x] T044 [US5] Verify `backend/app/execution/real.py` is not wired to `xt_account` client; leave stub behavior unchanged
- [x] T045 [US5] Audit `backend/app/xt_account/` and `backend/app/api/xt_account.py` for zero place/cancel/withdraw/transfer surfaces; remove any accidental trading or fund-movement hooks
- [x] T046 [US5] Confirm strategy modules do not import private XT client for order execution (`backend/app/strategy/` remains intent-only)
- [x] T047 [US5] Run US5 gates until green: `backend/tests/unit/test_real_execution_stub.py`, absence-of-trading-path cases in `backend/tests/contract/test_xt_account_api.py`, selected Simulation smoke under `backend/tests/`

**Checkpoint**: Account reads exist; live trading path remains closed

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Docs, quickstart validation, readiness for analyze/implement completion

- [x] T048 [P] Verify T002 placeholders remain accurate and add a short pointer from `README.md` to `specs/013-xt-account-private-api/quickstart.md` (do not duplicate full credential docs)
- [x] T049 [P] Update Feature 013 checklist notes in `specs/013-xt-account-private-api/checklists/requirements.md` (analyze remediations applied; implement next)
- [x] T050 Run full FR-017 automated gates listed in `specs/013-xt-account-private-api/quickstart.md` until green
- [x] T051 Manual UI pass per `specs/013-xt-account-private-api/quickstart.md` §3 plus ~375px / empty-loading-error checks per `docs/UI_UX_STANDARDS.md` (Simulation Portfolio vs Real XT separation; no trading controls)
- [x] T052 Mark Feature 013 DONE in `docs/ROADMAP.md` only after all acceptance gates pass (keep IN PROGRESS until then)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Start immediately
- **Phase 2 (Foundational)**: Depends on Setup — **blocks all stories**
- **Phase 3 (US1)**: After Foundational — MVP credential fail-closed
- **Phase 4 (US2)**: After US1 credential gate is in place (uses same service/API shell)
- **Phase 5 (US3)**: After Foundational; ideally after US2 normalize/API patterns exist (can parallelize UI panels with care)
- **Phase 6 (US4)**: After Foundational; should complete before calling feature “done” (error/rate-limit behavior used by US1–US3 reads)
- **Phase 7 (US5)**: After read paths exist (US2/US3) so absence-of-trading checks are meaningful
- **Phase 8 (Polish)**: After desired stories complete

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 Credentials | Phase 2 | Yes — fail-closed without balances UI |
| US2 Balances | Phase 2 + US1 gate | Yes — balances API/UI with fixtures |
| US3 Orders | Phase 2 (+ US2 patterns helpful) | Yes — orders API/UI with fixtures |
| US4 Errors/rate limit | Phase 2 | Yes — fixture-driven code map/retry tests |
| US5 Pipeline closed | US2/US3 surfaces present | Yes — stub + route absence + Simulation smoke |

### Parallel Opportunities

- T002 with T001
- T006, T010, T011, T012 after T003–T005 land
- Within a story: test tasks marked [P] can start together
- US4 error-map work can proceed in parallel with US2/US3 UI once client transport exists
- Frontend `xtAccountApi` + page shells can proceed once contract shapes are stable

### Parallel Example: User Story 2

```text
# After T017 (US1 gates) and foundational client shell:
T018 normalize balance tests
T019 balances contract tests
T020 portfolio isolation tests
# Then sequential implementation T021 → T023, then UI T024–T026
```

### Parallel Example: User Story 4

```text
T035 rate-limit/error unit tests
T036 contract error envelope tests
# Then T037–T039 mapping + UI error surfacing
```

---

## Implementation Strategy

### MVP first

Deliver **US1 + US2** first: fail-closed credentials + balances API + minimal Real XT page. That proves private connectivity and Portfolio isolation without orders UI.

### Incremental delivery

1. US1 credentials fail-closed  
2. US2 balances + inspect UI  
3. US3 open orders + status lookup  
4. US4 full error/rate-limit polish (if partial mapping already present, harden + tests)  
5. US5 explicit trading-path closure gates  
6. Polish / ROADMAP DONE

### Suggested commit style (only when user asks to commit)

- `feat: add xt_account signing and credential fail-closed`
- `feat: expose Real XT balances API and inspect UI`
- `feat: add Real XT open orders and order status reads`
- `feat: map private XT errors and bounded rate-limit retry`
- `test: lock RealExecutionAdapter unavailable and no place/cancel`

---

## Notes

- Do **not** implement XT place/cancel “for later” — FR-015 is unconditional.
- Do **not** merge Real XT into `/portfolio` snapshot or Feature 009 tables.
- Do **not** enable operator Real trading mode.
- Prefer injectable HTTP client / fakes over live XT in automated tests.
- Concrete constants: `recvWindow=5000`, `MAX_RETRY_AFTER_WAIT_S=3.0`, `SHORT_BACKOFF_S=0.5`.

---

## Phase 9: Amendment 2026-08-17 — Kraken private read

**Blocked on Feature 002 Phase 10 (Kraken public) complete.** Do not implement
these tasks before T052–T069 of Feature 002 are done. No Real Kraken orders.

- [ ] T053 Define venue-neutral `PrivateAccountPort` (balances, open orders,
      get order) in a core account module (e.g. `backend/app/account/port.py`)
      without Kraken/XT types (FR-018)
- [ ] T054 Implement Kraken private adapter (signing, balances, open orders,
      order lookup) in `backend/app/account/kraken_private.py` (or equivalent);
      keep `backend/app/xt_account/` (FR-019, FR-020, FR-022, FR-023)
- [ ] T055 [P] Load `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` fail-closed in
      credentials helper; placeholders only in `.env.example` (FR-021)
- [ ] T056 [P] Normalize Kraken private errors and bounded rate-limit retry
      (FR-024, FR-025)
- [ ] T057 HTTP read routes + Real Account UI (Venue: Kraken); no trading
      controls; do not write Simulation Portfolio (FR-026, FR-027)
- [ ] T058 [P] Tests: signing fixtures, credentials missing, normalize,
      isolation, no place/cancel, Strategy/Controller/Risk import guard
      (FR-030, SC-009–SC-013)
- [ ] T059 Confirm public market data still works without Kraken keys
      (FR-028)
- [ ] T060 Confirm RealExecutionAdapter still places no orders from 013
      (FR-029)

Do **not** start Feature 015 Kraken order placement in this phase.
