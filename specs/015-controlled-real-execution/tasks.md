# Tasks: Controlled Real Execution

**Input**: Design documents from `/specs/015-controlled-real-execution/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required — FR-010 / SC-001–SC-008 (confirmation gate, TTL, confirm
validation, auto exits, capital cap, Portfolio isolation, reconcile
ack≠fill, limit reject, Real blocked recovery / Resume, UI/API distinctness).
Prefer XT fakes/mocks; live smoke optional and credential-gated.

**Organization**: Extend existing Simulation session/pipeline + Execution +
`xt_account` only. Propose commits only; do not auto-commit. Keep Feature 015
`IN PROGRESS` on `docs/ROADMAP.md` until polish; mark Controlled Real MVP-2
only after quickstart gates pass.

**Spec locks** (must hold through all tasks):
- Same session/pipeline; explicit `mode=real`; no second engine (FR-001, Q1)
- Real MUST NOT write Simulation Portfolio holdings (FR-001a, SC-006)
- Exposure-increasing BUY requires confirmation; TTL 5 minutes; re-validate on
  confirm (FR-002/002a/002b, Q4)
- TP/SL, reducing SELL, emergency flatten skip entry confirm (FR-003)
- Hard cap allocatedCapital ≤ 50 USDT; maxPositionSize ≤ allocated (FR-004, Q3)
- XT free USDT gate before Real entry submit (FR-004a, I1)
- Real startingCapital / initial cash = local budget only — not XT cash
  (FR-004b, I2)
- Partial fill → record exposure + `RECOVERY_BLOCKED` (FR-006b, revised I3)
- ≤5s poll; timeout retains order + unsettled block until later reconcile
  (FR-006c, revised I4)
- RealExecutionAdapter sole XT write path; market orders only (FR-005, FR-006a, Q2)
- Submission ≠ fill; reconcile via 013; never invent fills (FR-006, Q2)
- Unmistakable Real UI/API; no Portfolio redesign (FR-007)
- No autonomous Real entries (FR-008)
- 025 TP/SL trigger semantics; Real fills from XT (FR-009)
- Real restart → blocked recovery; never auto-resume; do not extend 014 Sim
  auto-recovery (FR-011, Q5)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US4 map to spec stories

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/015-controlled-real-execution/`, `docs/ROADMAP.md`, `README.md`

---

## Phase 1: Setup

**Purpose**: Align docs and confirm touch points; no Real trading behavior yet

- [ ] T001 Verify Feature 015 is `IN PROGRESS` on `docs/ROADMAP.md` and branch is `015-controlled-real-execution`; confirm MVP-1 / 025 DONE and no Torque/GE/014-auto-recovery-for-Real scope creep
- [ ] T002 [P] Add brief Controlled Real operator notes to `README.md` (confirmed BUY; market only; ≤50 USDT; 5m pending TTL; blocked recovery; no Sim Portfolio writes) pointing at `specs/015-controlled-real-execution/` without inventing undocumented APIs

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Schema, Real create validation, pending model, XT market place
client, adapter scaffolding, and shared reason codes required by all stories

**⚠️ CRITICAL**: No user-story Real trading until this phase completes

- [ ] T003 Extend `SimulationSessionRow` (and add `PendingEntryConfirmationRow` and/or `RealOrderReconcileRow` as chosen in `data-model.md`) in `backend/app/db/models.py`; add `_ensure_column` / `create_all` support in `backend/app/db/session.py` `init_db()` for pending + Real order fields (`xt_order_id`, `reconcile_status`, etc.)
- [ ] T004 [P] Add stable Real reason/error codes (e.g. `real_capital_cap_exceeded`, `pending_confirmation_expired`, `confirm_validation_failed`, `limit_orders_unavailable`, `xt_reconcile_unsettled`, `resume_unavailable`, `no_pending_confirmation`) in `backend/app/simulation/control/reasons.py` and/or session error module used by API
- [ ] T005 Allow `mode="real"` create in `backend/app/simulation/session_service.py`: enforce `allocated_capital ≤ 50`, `0 < max_position_size ≤ allocated_capital`, one symbol; set `starting_capital = allocated_capital` and initial `cash` as **local budget only** (FR-004b — never treat/present as XT cash); require credentials at create; when XT balances readable, fail closed if free USDT < allocated (FR-004a); **skip** Simulation Portfolio reserve/bind/writes for Real; reject invalid Real config fail-closed; keep Simulation create path unchanged; expose `mode` and budget-vs-XT labeling in `session_to_dict`
- [ ] T006 [P] Implement `PendingEntryConfirmation` create/get/expire/discard helpers in `backend/app/simulation/pending_confirmation.py` (5-minute TTL; at most one `pending` per session; terminal statuses immutable) per `contracts/confirmation-gate.md` and `data-model.md`
- [ ] T007 [P] Add signed `place_market_order` (MARKET / SPOT only) on `XtPrivateClient` in `backend/app/xt_account/client.py` using Feature 013 signing; do **not** add public HTTP place/cancel/withdraw routes under `/xt-account/`
- [ ] T008 Replace Real stub body in `backend/app/execution/real.py` with adapter scaffold that still fails closed until wired (`credentials_missing` / controlled unavailable), rejects non-MARKET, and is the **only** intended caller of `place_market_order`; keep `ExecutionEngine` protocol in `backend/app/execution/port.py` (extend intent only if strictly required)
- [ ] T009 [P] Contract/create tests for Real mode bounds + Portfolio non-mutation at create in `backend/tests/contract/test_real_session_api.py` (and/or extend `backend/tests/contract/test_simulation_api.py`): `allocatedCapital > 50` → `real_capital_cap_exceeded`; valid Real create returns `mode: "real"`; Sim Portfolio holdings unchanged
- [ ] T010 [P] Unit tests for pending TTL helpers in `backend/tests/unit/test_real_pending_ttl.py` (expire after 5m; no reuse of expired intent)
- [ ] T011 [P] Assert Feature 013 HTTP surface still has no arbitrary place/cancel in `backend/tests/contract/test_xt_account_api.py` while allowing `XtPrivateClient.place_market_order` to exist for adapter use

**Checkpoint**: Real create + schema + pending helpers + XT place client + adapter scaffold ready; pipeline still Simulation-only for fills until US1

---

## Phase 3: User Story 1 - Confirmed real entry (Priority: P1) 🎯 MVP

**Goal**: Exposure-increasing Real BUY waits for operator confirmation; confirm
re-validates then places market order via RealExecutionAdapter; decline/expiry/
validation failure place nothing; fills only after reconcile evidence

**Independent Test**: Fake XT client; Risk-approved BUY → pending; no place
until confirm; confirm within TTL → place + reconcile fill; expire/decline/
confirm-fail → no order / no phantom position

### Tests for User Story 1

- [ ] T012 [P] [US1] Unit/pipeline tests for confirmation gate in `backend/tests/unit/test_real_confirmation_gate.py` (BUY after Risk does not call place; decline/stop discard; confirm-time validation failure clears/rejects with no XT)
- [ ] T013 [P] [US1] Contract tests for confirm/decline routes in `backend/tests/contract/test_real_session_api.py` (`POST .../confirm-entry`, `POST .../decline-entry`; expired → `pending_confirmation_expired`)
- [ ] T014 [P] [US1] Adapter unit tests with fake XT in `backend/tests/unit/test_real_execution_adapter.py` (place ack alone does not yield filled `FillResult`; filled only after get_order/reconcile evidence)

### Implementation for User Story 1

- [ ] T015 [US1] Branch Real path in `backend/app/simulation/pipeline.py`: after Controller+Risk APPROVE exposure-increasing BUY, create pending confirmation and **do not** call RealExecutionAdapter; expose `pendingConfirmation` via `session_to_dict` / status
- [ ] T016 [US1] Wire worker/pipeline to expire pendings (TTL) without stopping session; discard pending on session stop in `backend/app/simulation/session_service.py` / `pending_confirmation.py`
- [ ] T017 [US1] Implement confirm-entry final validation (mark trust, risk, capital cap, flat→long rules, **XT free USDT ≥ intended notional** per FR-004a) then call RealExecutionAdapter market BUY in `backend/app/simulation/session_service.py` (or dedicated confirm module); decline-entry discards without XT
- [ ] T018 [US1] Complete `RealExecutionAdapter.execute` in `backend/app/execution/real.py`: MARKET place via `XtPrivateClient`, poll/reconcile with **≤5s** budget; apply fills only from XT evidence; on timeout **retain `xt_order_id`**, set unsettled, block new orders (FR-006c); on partial fill record exposure and signal caller to enter `RECOVERY_BLOCKED` (FR-006b); apply Real session cash/position **without** Portfolio mutations and without treating budget cash as XT cash
- [ ] T019 [US1] Add FastAPI routes confirm-entry / decline-entry in `backend/app/api/simulation.py` per `contracts/session-real-api.md`
- [ ] T020 [US1] Select RealExecutionAdapter for `mode=real` in pipeline/execution wiring (Simulation adapter remains for `mode=simulation`)
- [ ] T021 [US1] Minimal frontend: Real pending confirm/decline UI + API client in `frontend/src/services/simulationApi.ts`, `frontend/src/features/simulation/SessionStatusPanel.tsx` and/or `SimulationSessionDetailPage.tsx`, `useSimulationSession.ts`
- [ ] T022 [P] [US1] Frontend smoke test for pending confirm actions in `frontend/src/__tests__/controlledRealUi015.test.tsx` (~375px)

**Checkpoint**: US1 MVP — confirmed Real entry works end-to-end with fakes

---

## Phase 4: User Story 2 - Automatic protective and reducing exits (Priority: P1)

**Goal**: TP/SL, reducing strategy SELL, and emergency/STOP flatten execute
without entry confirmation when a safe Real path exists; fills via Real
adapter + reconcile

**Independent Test**: Open Real long (confirmed); trigger TP or SL or strategy
SELL or stop flatten; assert no confirm gate; position updates only after
reconcile

### Tests for User Story 2

- [ ] T023 [P] [US2] Unit/pipeline tests in `backend/tests/unit/test_real_auto_exits.py` (protective TP/SL skip confirm; reducing SELL skip confirm; forced flatten skip confirm; precedence session/emergency → SL → TP → strategy preserved)

### Implementation for User Story 2

- [ ] T024 [US2] Ensure Real protective TP/SL evaluation (025 rules) emits SELL through Controller → Risk → RealExecutionAdapter without pending confirmation in `backend/app/simulation/pipeline.py`
- [ ] T025 [US2] Ensure Real strategy reducing/closing SELL and emergency/STOP flatten paths skip confirmation gate and use RealExecutionAdapter in `backend/app/simulation/pipeline.py` / `session_service.py`
- [ ] T026 [US2] Reconcile-driven apply of Real SELL fills to session state without Simulation Portfolio writes in session apply-fill / accounting path

**Checkpoint**: US2 — Real risk-reducing exits automatic and safe

---

## Phase 5: User Story 3 - Bounded Real session shape + unmistakable UI (Priority: P1)

**Goal**: Real sessions limited to one pair / one long / ≤50 USDT; Real mode
unmistakable in UI and history; cap enforced again at confirm/submit

**Independent Test**: Oversized create rejected; UI shows REAL distinctly;
confirm blocked if cap would be violated; history/provenance shows real

### Tests for User Story 3

- [ ] T027 [P] [US3] Unit/contract tests for pre-submit cap re-check, single-long enforcement, and **XT free &lt; notional → no place** in `backend/tests/unit/test_real_capital_bounds.py` (and extend contract tests)
- [ ] T028 [P] [US3] Portfolio isolation regression in `backend/tests/unit/test_real_portfolio_isolation.py` (Real fills never mutate Sim Portfolio holdings/allocations)
- [ ] T029 [P] [US3] Extend frontend test in `frontend/src/__tests__/controlledRealUi015.test.tsx` for unmistakable Real label/mode on create/status/history (~375px)

### Implementation for User Story 3

- [ ] T030 [US3] Re-enforce 50 USDT cap and position bounds at confirm and immediately before XT entry submit in confirm path / `RealExecutionAdapter`
- [ ] T031 [US3] Ensure status, list, history, and journals expose explicit `mode: "real"` / provenance and label Real `startingCapital`/budget cash as **local budget not XT cash** (optional `xtFreeQuote` when reconciled) in `session_service.py` and related serializers
- [ ] T032 [US3] Frontend Real mode selector/create fields and unmistakable badges in `frontend/src/features/simulation/SessionConfigForm.tsx`, `SimulationBadge.tsx`, `SimulationHistoryList.tsx`; budget fields must not read as XT cash (no Portfolio redesign; no new primary nav)
- [ ] T033 [US3] Reject multi-pair / multi-position Real configuration attempts fail-closed in `session_service.py` (keep one-symbol session invariant)

**Checkpoint**: US3 — blast radius bounds + clear Real UX

---

## Phase 6: User Story 4 - Reconcile over assume (Priority: P2)

**Goal**: XT reject/timeout/unclear/partial states never invent truth; partial
records exposure then blocks; timeout retains order and blocks until later
reconcile; limit orders unavailable

**Independent Test**: Fake XT reject, timeout (order retained + blocked),
partial (exposure + blocked), ack-without-fill; limit placement rejected

### Tests for User Story 4

- [ ] T034 [P] [US4] Reconcile failure-mode tests in `backend/tests/unit/test_real_execution_adapter.py` (or `test_real_reconcile.py`): reject → no fill; submission-only ack → no invented fill; **partial → exposure recorded + blocked**; **timeout → retain order id + unsettled block** (no forgotten order)
- [ ] T035 [P] [US4] Limit-order rejection test (`limit_orders_unavailable`) in `backend/tests/unit/test_real_execution_adapter.py` / contract coverage

### Implementation for User Story 4

- [ ] T036 [US4] Harden Real order reconcile state machine in adapter + `data-model` fields (`submit_status`, `reconcile_status` incl. `partial_filled_blocked` / `unsettled`) so pipeline never promotes submit-alone to filled; on partial apply exposure then transition session to `RECOVERY_BLOCKED` in `pipeline.py` / `session_service.py`; on timeout retain `xt_order_id`, unsettle, block new orders until later reconcile (FR-006b/c)
- [ ] T037 [US4] Map XT private errors (credentials, rate limit, timestamp_invalid, unavailable, insufficient free) to fail-closed session/confirm outcomes without inventing balances
- [ ] T038 [US4] Explicitly reject limit/non-market Real placement attempts at API/adapter boundary

**Checkpoint**: US4 — reconcile authority proven under failure

---

## Phase 7: Real blocked recovery (FR-011 / SC-008)

**Goal**: After restart, Real sessions block; discard pendings; never
auto-resume; operator Resume only after safe reconcile + risk re-check, or
Stop/Flatten

**Independent Test**: Simulated restart leaves Real `RECOVERY_BLOCKED`; no
strategy orders; Resume unavailable until gates pass; Simulation 014
auto-recovery unchanged

### Tests

- [ ] T039 [P] Unit/integration tests in `backend/tests/unit/test_real_blocked_recovery.py` (Real orphan → blocked; pendings discarded; no auto-resume; partial/unsettled in-session block; Resume fail/success after later reconcile; Sim path unchanged)
- [ ] T040 [P] Frontend blocked-recovery banner smoke in `frontend/src/__tests__/controlledRealUi015.test.tsx`

### Implementation

- [ ] T041 Branch startup recovery in `backend/app/simulation/recovery.py`: for `mode=real`, always `RECOVERY_BLOCKED`, discard pendings, reconcile via 013, **never** auto-resume; keep Feature 014 Sim conditional auto-recovery for `mode=simulation`
- [ ] T042 Gate Real Resume in `backend/app/simulation/session_service.py` on Real reconcile + safety/risk re-check (`resume_unavailable` when incomplete/contradictory)
- [ ] T043 Ensure Stop/Flatten from Real blocked/running skips entry confirmation and uses reconciled trustworthy state when executable
- [ ] T044 Frontend blocked-recovery messaging + Resume/Stop affordances in `SessionStatusPanel.tsx` / `SimulationSessionDetailPage.tsx`

**Checkpoint**: FR-011 / SC-008 green; Sim recovery not extended into Real

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Quickstart validation, docs, MVP-2 readiness

- [ ] T045 [P] Run and fix `specs/015-controlled-real-execution/quickstart.md` automated pytest + frontend test commands until green
- [ ] T046 [P] Update `README.md` Controlled Real notes if API/UI names drifted during implementation
- [ ] T047 Mark Feature 015 / Controlled Real MVP-2 acceptance notes on `docs/ROADMAP.md` only after SC-001–SC-008 evidence (keep honest `IN PROGRESS` until then; set DONE when operator accepts)
- [ ] T048 Confirm existing Simulation/Backtest/012 stub regression suite still green (`backend/tests/unit/test_real_execution_stub.py` behavior updated or replaced only as appropriate for live adapter + miswire cases)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: immediate
- **Phase 2 Foundational**: after Setup — **BLOCKS** all user stories
- **Phase 3 US1**: after Foundational — MVP
- **Phase 4 US2**: after US1 (needs Real long via confirmed entry path or test fixture that injects Real long + adapter)
- **Phase 5 US3**: after Foundational; UI can parallelize with late US1; cap re-check depends on confirm path (US1)
- **Phase 6 US4**: after US1 adapter (deepens reconcile); can overlap late US2
- **Phase 7 Blocked recovery**: after US1 pending + Real mode create; ideally after US4 reconcile helpers
- **Phase 8 Polish**: after desired stories + Phase 7

### User Story Dependencies

- **US1 (P1)**: Foundational only — MVP
- **US2 (P1)**: Practically after US1 Real adapter + session long state
- **US3 (P1)**: Foundational for create bounds; confirm-time cap after US1; UI parallelizable
- **US4 (P2)**: After US1 adapter scaffold; strengthens failure modes used by US2/US7

### Parallel Opportunities

- T002 || docs; T004 || T006 || T007 within Foundational after T003 starts
- T009 || T010 || T011 after helpers exist
- T012 || T013 || T014 before/during US1 implementation
- T023 || US2 tests; T027 || T028 || T029 for US3
- T034 || T035 for US4; T039 || T040 for recovery
- T045 || T046 in polish

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Unit/pipeline tests for confirmation gate in backend/tests/unit/test_real_confirmation_gate.py"
Task: "Contract tests for confirm/decline routes in backend/tests/contract/test_real_session_api.py"
Task: "Adapter unit tests with fake XT in backend/tests/unit/test_real_execution_adapter.py"

# Then implementation sequentially:
Task: "Branch Real BUY → pending in pipeline.py"
Task: "Confirm/decline + RealExecutionAdapter + API routes"
Task: "Minimal confirm UI + smoke test"
```

---

## Parallel Example: User Story 3

```bash
Task: "Capital bounds tests in backend/tests/unit/test_real_capital_bounds.py"
Task: "Portfolio isolation tests in backend/tests/unit/test_real_portfolio_isolation.py"
Task: "Frontend Real label tests in frontend/src/__tests__/controlledRealUi015.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational
3. Phase 3 US1 (confirmed entry + fake XT)
4. **STOP and VALIDATE** gate independently
5. Then US2 → US3 → US4 → blocked recovery → polish

### Incremental Delivery

1. Setup + Foundational → Real create + pending schema
2. US1 → confirmed entry MVP
3. US2 → automatic exits
4. US3 → bounds + unmistakable UI
5. US4 → reconcile failure hardening
6. Phase 7 → Real blocked recovery
7. Polish → quickstart / ROADMAP honesty

### Suggested MVP scope

**US1 only** (Phases 1–3): operator can confirm a Real BUY with fakes and never
auto-enter. Do not claim MVP-2 DONE until US2–US4 + Phase 7 + quickstart also
pass (roadmap Controlled Real MVP includes exits, bounds, reconcile, recovery).

---

## Notes

- [P] = different files, no incomplete dependencies
- [Story] labels US1–US4 only on story-phase tasks
- All tasks use checklist format with Task ID and file paths
- Prefer XT fakes in CI; optional live smoke is manual/gated
- Do not extend Feature 014 Simulation auto-recovery into Real
- Commit only when explicitly asked
