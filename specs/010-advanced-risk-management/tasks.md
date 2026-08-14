# Tasks: Advanced Risk Management

**Input**: Design documents from `/specs/010-advanced-risk-management/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required — Risk unit tests, Simulation/Portfolio contract tests,
Backtest regression, frontend Simulation/Settings risk fields (SC-001–SC-005,
SC-006–SC-008).

**Organization**: Extend existing Simulation Risk + Feature 009 Portfolio.
Do **not** create a second risk engine. Dual ledger retained. Daily loss /
drawdown stop / wallet unification out of scope. Propose commits only; do not
auto-commit. Keep Feature 010 `IN PROGRESS` on `docs/ROADMAP.md` until
completion workflow.

**Spec precedence** (clarify 2026-08-14):
- Create/start: `allocated_capital ≤ portfolio.available`
- Bound BUY: allocation remaining only; unbound BUY does not re-check available
- Never `available − deployed`
- Max-loss: frozen baseline kind; uncomputable → reject BUYs, no invented stop
- Bound allocation: reject release; resize only if reserved ≥ deployed
- First failing catalog reason; code ≠ message
- Per-symbol: projected post-BUY weight; fail closed; USDT uncapped
- Backtest: same RiskManager, portfolio context off

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/010-advanced-risk-management/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

**Purpose**: Confirm extension surfaces; no new risk package

- [X] T001 Confirm reusable Risk/Simulation/Portfolio/Settings surfaces per plan.md (`backend/app/simulation/control/risk.py`, `backend/app/simulation/pipeline.py`, `backend/app/simulation/session_service.py`, `backend/app/portfolio/`, `backend/app/settings/`, `backend/app/backtest/engine.py`, frontend simulation/settings) — extend; do not create `app.risk_engine`
- [X] T002 [P] Confirm Feature 004 Backtest already imports shared `RiskManager` in `backend/app/backtest/engine.py` (portfolio context will stay off)

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Shared reason catalog, schema fields, RiskContext portfolio hooks

- [X] T003 Create shared reason catalog module `backend/app/simulation/control/reasons.py` per `contracts/risk-catalog.md` (stable codes + default messages; retain existing 003/004 meanings; add portfolio-aware codes)
- [X] T004 [P] Extend `SimulationSessionRow` in `backend/app/db/models.py` with nullable `allocation_id`, `portfolio_max_loss_rate`, `portfolio_max_loss_amount`, `portfolio_loss_baseline_kind`, `portfolio_loss_baseline_value`, `per_symbol_max_weight` per `data-model.md`
- [X] T005 [P] Ensure SQLite column add/migrate path for new session risk fields in `backend/app/db/session.py` (fail-closed compatible with existing ensure_* patterns)
- [X] T006 Extend `RiskContext` / `RiskDecision` in `backend/app/simulation/control/risk.py` with optional portfolio context fields (available unused on BUY unbound; allocation remaining; baseline kind/value/bound; per-symbol cap; quotes/holdings snapshot hooks) and wire **first-fail precedence** per FR-002a / `contracts/risk-catalog.md`
- [X] T007 [P] Unit tests for catalog code≠message and precedence ordering skeleton in `backend/tests/unit/test_risk_catalog.py` / `backend/tests/unit/test_risk_precedence.py`
- [X] T008 Refactor existing Risk reject strings in `backend/app/simulation/control/risk.py` (and Controller where practical) to use catalog codes/messages without changing 003/004 semantics
- [X] T009 Run existing `backend/tests/unit/test_risk_rejects.py` and `backend/tests/unit/test_max_trades.py` — stay green after catalog refactor

**Checkpoint**: Catalog + schema + RiskContext ready; no portfolio gates enforced yet beyond scaffolding

---

## Phase 3: User Story 1 - Simulation respects Portfolio capital (Priority: P1) 🎯 MVP

**Goal**: Create/start rejects when allocated > Portfolio available; unbound BUY does not re-check available.

**Independent Test**: Fund 1000, reserve 400, create with allocated 700 → reject; allocated 600 → ok. Unbound BUY uses session gates only for Portfolio available.

### Tests

- [X] T010 [P] [US1] Contract tests in `backend/tests/contract/test_simulation_api.py`: create/start `insufficient_portfolio_available` when allocated > available; success when allocated ≤ available per SC-001
- [X] T011 [P] [US1] Unit tests in `backend/tests/unit/test_risk_portfolio_available.py`: unbound BUY does not fail solely on Portfolio available; session cash/allocated/max-position still apply

### Implementation

- [X] T012 [US1] In `backend/app/simulation/session_service.py` (create/start), load Feature 009 Portfolio available and reject when `allocated_capital > available` with catalog code `insufficient_portfolio_available` per FR-004 / `contracts/simulation-risk-api.md`
- [X] T013 [US1] Persist new optional create fields when present (allocationId / portfolio max-loss / per-symbol) onto session row without enforcing US2–US4 gates yet in `backend/app/simulation/session_service.py` / API body models in `backend/app/api/simulation.py`
- [X] T014 [US1] Extend create form types/UI in `frontend/src/features/simulation/` and `frontend/src/services/` to show Portfolio available vs allocated validation error (clear message, not hover-only)
- [X] T015 [US1] Run T010–T011; fix until passing

**Checkpoint**: MVP — Portfolio available protects create/start

---

## Phase 4: User Story 2 - Per-allocation exposure limits (Priority: P1)

**Goal**: Optional allocation binding; BUY limited by reserved − deployed; resize/release guards while bound.

**Independent Test**: Bind to 200 reserved allocation; oversize BUY rejected; release blocked while bound; resize below deployed rejected.

### Tests

- [X] T016 [P] [US2] Unit/contract tests: bound BUY exceeding remaining → `allocation_exposure_exceeded`; unbound invents no binding — in `backend/tests/unit/test_risk_allocation_binding.py` and/or `backend/tests/contract/test_simulation_api.py` per SC-002
- [X] T017 [P] [US2] Contract tests in `backend/tests/contract/test_portfolio_api.py`: DELETE allocation while bound → `allocation_release_blocked`; PATCH reserved < deployed → `allocation_resize_blocked`

### Implementation

- [X] T018 [US2] Validate `allocationId` exists on create; compute binding deployed from session `cost_basis` when long in `backend/app/simulation/session_service.py` / Risk context builder in `backend/app/simulation/pipeline.py`
- [X] T019 [US2] Enforce allocation remaining on BUY in `backend/app/simulation/control/risk.py` (intended notional ≤ reserved − deployed) per research Decision 3/9
- [X] T020 [US2] Enforce release/resize guards in `backend/app/portfolio/service.py` (and API) while any Simulation is bound per FR-006
- [X] T021 [US2] Frontend: optional allocation bind control on Simulation create in `frontend/src/features/simulation/` (list allocations from Portfolio API)
- [X] T022 [US2] Run T016–T017; fix until passing

**Checkpoint**: Allocation sleeves are real when bound

---

## Phase 5: User Story 5 - Shared reasons & persisted effective risk config (Priority: P1)

**Goal**: Journals show catalog code+message; Settings defaults copy-at-create; Settings edits do not rewrite sessions.

**Independent Test**: Reject with portfolio code; change Settings; session effective fields unchanged.

### Tests

- [X] T023 [P] [US5] Contract/unit: decision journal stores first failing `reasonCode` + separate `reasonMessage` in `backend/tests/contract/test_simulation_api.py` / unit risk tests per FR-002 / FR-011
- [X] T024 [P] [US5] Settings defaults copy + immutability: create session from Settings; change Settings; session fields unchanged — `backend/tests/unit/test_settings_service.py` and/or contract tests per SC-006

### Implementation

- [X] T025 [US5] Extend Settings model/API/UI for optional `portfolioMaxLossRate` / `portfolioMaxLossAmount` / `perSymbolMaxWeight` / `preferredAllocationId` in `backend/app/settings/`, `backend/app/db/models.py`, `frontend/src/features/settings/` per Feature 008 pattern (defaults only)
- [X] T026 [US5] Prefill Simulation create from Settings in frontend; persist effective risk snapshot on session create in `backend/app/simulation/session_service.py`
- [X] T027 [US5] Ensure pipeline/journal path writes catalog message for new codes in `backend/app/simulation/session_service.py` `add_decision` / stop reasons
- [X] T028 [US5] Frontend journal/status display shows reason code + message clearly in `frontend/src/features/simulation/`
- [X] T029 [US5] Run T023–T024; fix until passing

**Checkpoint**: Traceable reasons + frozen effective config

---

## Phase 6: User Story 3 - Portfolio max-loss stop (Priority: P1)

**Goal**: Freeze baseline at start; stop when loss ≥ bound; uncomputable → BUY reject only.

**Independent Test**: Configure small max-loss; reach bound → `portfolio_max_loss` stop. Incomplete equity under equity baseline → BUYs blocked with `portfolio_max_loss_uncomputable`.

### Tests

- [X] T030 [P] [US3] Unit tests: freeze kind equity vs quote_cash; loss = baseline − current; uncomputable rejects BUY without stop; reached triggers stop — `backend/tests/unit/test_risk_portfolio_max_loss.py` per SC-003
- [X] T031 [P] [US3] Confirm Backtest path unaffected (no portfolio max-loss) in `backend/tests/contract/test_backtest_api.py` or unit engine test

### Implementation

- [X] T032 [US3] On Simulation start, persist `portfolio_loss_baseline_kind` / `value` and derive amount from rate when needed in `backend/app/simulation/session_service.py`
- [X] T033 [US3] Evaluate portfolio max-loss in `backend/app/simulation/control/risk.py` + pipeline stop wiring in `backend/app/simulation/pipeline.py` (forced flatten remains Feature 003)
- [X] T034 [US3] Simulation UI fields for portfolio max-loss (rate and/or amount) in `frontend/src/features/simulation/` with contextual help
- [X] T035 [US3] Run T030–T031; fix until passing

**Checkpoint**: One clear Portfolio max-loss stop

---

## Phase 7: User Story 4 - Optional per-symbol exposure (Priority: P2)

**Goal**: Optional weight cap on projected post-BUY non-quote weight.

**Independent Test**: Cap set → violating BUY rejected; unset → no cap; missing price → fail closed.

### Tests

- [X] T036 [P] [US4] Unit tests: projected post-BUY weight; stale per Feature 002; missing/incomplete fail closed; USDT uncapped — `backend/tests/unit/test_risk_per_symbol.py` per SC-004

### Implementation

- [X] T037 [US4] Enforce per-symbol cap in `backend/app/simulation/control/risk.py` using Portfolio holdings + public quotes (projected post-BUY)
- [X] T038 [US4] Simulation + Settings UI for optional `perSymbolMaxWeight` in `frontend/src/features/simulation/` and `frontend/src/features/settings/`
- [X] T039 [US4] Run T036; fix until passing

**Checkpoint**: Optional concentration guardrail

---

## Phase 8: Polish & Cross-Cutting

- [X] T040 Ensure Backtest/Comparison call shared `RiskManager` with portfolio context disabled in `backend/app/backtest/engine.py` (and comparison path if applicable) — no second engine
- [X] T041 [P] Re-run Simulation + Backtest contracts: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q` per SC-005
- [X] T042 [P] Frontend tests for create validation, bind control, settings defaults, journal reason display in `frontend/src/__tests__/` per SC-007 / SC-008
- [X] T043 Execute automated checks in `specs/010-advanced-risk-management/quickstart.md`
- [X] T044 [P] UI review vs `docs/UI_UX_STANDARDS.md` (375px, help not hover-only, Simulation obvious)
- [X] T045 Confirm no XT private / real-money / daily loss / drawdown-stop / wallet unification / second Risk package
- [X] T046 Keep Feature 010 `IN PROGRESS` in `docs/ROADMAP.md`; do not mark DONE; do not start Feature 011
- [X] T047 Propose commit message (do not auto-commit)

---

## Dependencies

```text
T001–T009 foundation (catalog, schema, RiskContext, precedence)
   │
   ▼
 US1 available at create/start (MVP)
   │
   ├──────────────────► US5 reasons persistence + Settings defaults
   ▼
 US2 allocation binding + resize/release guards
   │
   ├──────────────────► US3 portfolio max-loss
   └──────────────────► US4 per-symbol (P2)
   │
   ▼
 Polish (Backtest off-context, regression, UI, quickstart)
```

## Parallel opportunities

- T004/T005 schema work alongside T003 catalog
- T010/T011 tests before/with T012
- T016/T017 tests in parallel
- T023/T024 in parallel
- T030/T031 in parallel
- T041/T042/T044 polish in parallel

## Implementation strategy

### MVP first

1. Phase 1–2 foundation  
2. Phase 3 US1 (available at create/start)  
3. Stop and validate SC-001  

### Incremental

US1 → US2 → US5 → US3 → US4 → Polish  

## Task summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 47 (T001–T047) |
| **US1** | T010–T015 |
| **US2** | T016–T022 |
| **US5** | T023–T029 |
| **US3** | T030–T035 |
| **US4** | T036–T039 |
| **Setup + Foundational + Polish** | T001–T009, T040–T047 |

## Notes

- [P] = different files / parallelizable
- [USn] maps to spec user stories
- Trading-critical: keep existing risk/max-trades tests green after catalog refactor
- Propose commits only
