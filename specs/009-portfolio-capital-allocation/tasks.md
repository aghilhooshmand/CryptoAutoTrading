# Tasks: Portfolio & Capital Allocation Core

**Input**: Design documents from `/specs/009-portfolio-capital-allocation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required — portfolio unit/contract, frontend Portfolio, Simulation/Backtest regression.

**Organization**: T001–T043 delivered the reusable 009 package (identity,
allocations, funding, valuation, snapshots) under a **superseded**
operator model (manual holdings book). This list is the **remaining
correction** to the locked Simulation Portfolio direction. Do not restart
Feature 010. Propose commits only.

**Spec precedence** (Session 2026-08-14 Simulation Portfolio):
- Simulation Portfolio only; provenance `simulation`
- Operator funds USDT only; no public holdings upsert/UI for BTC/ETH/SOL
- Non-USDT holdings from simulated fills (Execution → Portfolio/Accounting)
- `available = quote_cash − reserved`; allocations kept but compact in UI
- Feature 002 public quotes; never invent prices; USDT has no artificial unrealized P&L
- Snapshots on funding / simulation_fill / allocation_*; no history charts
- Package: `backend/app/portfolio/`

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `specs/009-portfolio-capital-allocation/`, `docs/ROADMAP.md`

---

## Phase 1: Setup

- [X] T044 Confirm reusable 009 surfaces (`backend/app/portfolio/`, `backend/app/api/portfolio.py`, `frontend/src/pages/PortfolioPage.tsx`, `frontend/src/features/portfolio/`, `frontend/src/services/portfolioApi.ts`) per plan.md — extend; do not create a second portfolio package
- [X] T045 [P] Confirm Feature 003 `_apply_fill` in `backend/app/simulation/session_service.py` as the only fill hook for 009 (pipeline already calls it; strategies must not write portfolio)

---

## Phase 2: Foundational (blocks stories)

**Purpose**: Remove operator holdings writes; simulation provenance; fill-apply domain API

- [X] T046 Remove public `PUT /portfolio/holdings` and `DELETE /portfolio/holdings/{asset}` from `backend/app/api/portfolio.py`; those paths MUST return 404 or 405 per `contracts/portfolio-api.md`
- [X] T047 [P] Migrate `local_manual` → `simulation` for portfolio/holdings provenance in `backend/app/portfolio/repository.py` / `backend/app/db/session.py`; GET snapshot `bookProvenance` and holding `provenance` are `simulation`
- [X] T048 Implement `apply_simulation_fill` in `backend/app/portfolio/service.py` (BUY/SELL qty + cash_delta + fill price; weighted average cost; realized P&L on sell; delete row at qty 0; no negative USDT; persist `fillApplyWarning` on refuse and skip `simulation_fill` snapshot; clear warning on success; snapshot reason `simulation_fill` only on success) per `data-model.md` / research Decision 3
- [X] T049 [P] Set USDT inspection `unrealizedPnl` and `return` to `null` in `backend/app/portfolio/service.py` (no artificial USDT unrealized P&L) per FR-001b
- [X] T050 [P] Contract tests in `backend/tests/contract/test_portfolio_api.py`: funding still works; `PUT /portfolio/holdings` is 404/405; GET has `bookProvenance` `simulation` and no requirement for operator BTC upsert
- [X] T051 [P] Unit tests in `backend/tests/unit/test_portfolio_service.py`: BUY then SELL updates USDT/BTC/cost/realized P&L; insufficient USDT leaves holdings unchanged, sets fill-apply warning, no snapshot; GET does not snapshot; allocation identity unchanged
- [X] T052 Run Simulation/Backtest regression: `pytest backend/tests/contract/test_simulation_api.py backend/tests/contract/test_backtest_api.py -q`

**Checkpoint**: Public manual holdings API gone; fill-apply exists as domain API

---

## Phase 3: User Story 1 - Inspect Simulation Portfolio (Priority: P1) 🎯 MVP

**Goal**: Fund USDT; exchange-style summary; no crypto-entry form; Simulation obvious.

### Tests

- [X] T053 [P] [US1] Frontend tests in `frontend/src/__tests__/portfolio.test.tsx`: summary cards; fund USDT; no holding asset/qty form; Simulation label; GET `warning` shown when present; no “local/manual holdings book” copy per FR-010 / SC-001 / SC-009
- [X] T054 [P] [US1] Contract GET unfunded + after funding: USDT only, `mode`/`bookProvenance` simulation, in `backend/tests/contract/test_portfolio_api.py`

### Implementation

- [X] T055 [US1] Rework `frontend/src/pages/PortfolioPage.tsx` and `frontend/src/features/portfolio/` into Simulation Portfolio: summary cards (total value, available USDT, total P&L/return, realized/unrealized); remove HoldingsPanel record/remove form; strip sandbox wording; show GET `warning` when present (not hover-only)
- [X] T056 [US1] Keep funding as a compact control in `frontend/src/features/portfolio/PortfolioCapitalPanel.tsx` (simulation USDT, not “set equity”)
- [X] T057 [US1] Extend `frontend/src/services/portfolioApi.ts` types (`mode`, `bookProvenance` simulation, nullable USDT unrealized, `warning`, `positions`); remove `putHolding` / `deleteHolding` clients
- [X] T058 [US1] Run T053–T054; fix until passing

**Checkpoint**: MVP inspect + fund without a manual holdings book

---

## Phase 4: User Story 2 - Holdings follow simulated execution (Priority: P1)

**Goal**: Simulation fills write USDT/BTC (etc.) through the pipeline.

### Tests

- [X] T059 [P] [US2] Unit/contract tests: `apply_simulation_fill` BUY 200 USDT → BTC qty up / USDT down; SELL reverses + realized P&L; strategies not called, in `backend/tests/unit/test_portfolio_service.py` and/or `backend/tests/contract/test_portfolio_api.py` per SC-009
- [X] T060 [P] [US2] Test that Feature 003 `_apply_fill` invokes portfolio apply after the journal row is added; refused apply does not roll back journals and GET `warning` is set, in `backend/tests/unit/` or simulation contract tests per FR-009 / SC-009

### Implementation

- [X] T061 [US2] Hook `apply_simulation_fill` from `backend/app/simulation/session_service.py` `_apply_fill` after the trade journal is added (symbol → base asset); catch refused apply; do not raise out of the session transaction; do not hook strategy modules
- [X] T062 [US2] Surface fill-created holdings on GET (valuation unchanged) in `backend/app/portfolio/service.py`
- [X] T084 [US2] Derive `deployed` and `positions` on GET from Feature 003 sessions in `RUNNING`/`STOPPING` with a long position (`sessionId`, `symbol`, `asset`, `side`, `quantity`, `costBasis`); leftover `portfolio.deployed` is not authority, in `backend/app/portfolio/service.py` per research Decision 3b / FR-001
- [X] T085 [P] [US2] Tests: active long session → non-empty `positions` and `deployed` = cost basis; no active long → `"0"` / `[]`; refused apply → warning + unchanged holdings, in `backend/tests/unit/test_portfolio_service.py` and/or `backend/tests/contract/test_portfolio_api.py`
- [X] T063 [US2] Run T059–T060 and T085; fix until passing

**Checkpoint**: Example BUY/SELL lifecycle visible on Simulation Portfolio

---

## Phase 5: User Story 3 - Compact capital reservation (Priority: P2)

**Goal**: Allocations remain correct; UI is secondary.

### Tests

- [X] T064 [P] [US3] Contract tests: POST/PATCH/DELETE allocations vs USDT cash; over-reserve 400; shared `targetRef`; funding reject when cash < reserved, in `backend/tests/contract/test_portfolio_api.py`
- [X] T065 [P] [US3] Frontend tests: compact Capital (available/reserved/deployed); allocation CRUD not page-primary; overspend error; confirm release, in `frontend/src/__tests__/portfolio.test.tsx`

### Implementation

- [X] T066 [US3] Keep allocation service invariants in `backend/app/portfolio/service.py`
- [X] T067 [US3] Demote `frontend/src/features/portfolio/AllocationPanel.tsx` to expandable/compact Capital; parent page leads with summary + holdings
- [X] T068 [US3] Run T064–T065; fix until passing

**Checkpoint**: SC-002 with secondary allocation UI

---

## Phase 6: User Story 4 - Persist (Priority: P1)

### Tests

- [X] T069 [P] [US4] Contract: fund + fill-apply + allocation; GET unchanged after failed over-reserve, in `backend/tests/contract/test_portfolio_api.py` per FR-007 / SC-003
- [X] T070 [P] [US4] Unit: funding / simulation_fill / allocation each insert one snapshot; GET does not, in `backend/tests/unit/test_portfolio_service.py` per FR-007a

### Implementation

- [X] T071 [US4] Snapshot reasons include `simulation_fill` only from a **successful** `apply_simulation_fill` (do not insert on refuse or GET) in `backend/app/portfolio/repository.py` / `service.py`
- [X] T072 [US4] Run T069–T070; fix until passing

**Checkpoint**: SC-003

---

## Phase 7: User Story 5 - Current-state analytics (Priority: P2)

### Tests

- [X] T073 [P] [US5] Unit/contract: missing quote → excluded + `equityComplete` false (value not `"0"`); stale included; unknown cost null P&L; USDT unrealized null, in `backend/tests/unit/test_portfolio_valuation.py` and/or contract tests per FR-011a / SC-008
- [X] T074 [P] [US5] Frontend: partial equity labeled; stale indicator; weight visual present; no drawdown/value-over-time; holdings cards usable ~375px, in `frontend/src/__tests__/portfolio.test.tsx` per SC-006 / SC-007

### Implementation

- [X] T075 [US5] Add current-state allocation visual (donut or equivalent) in `frontend/src/features/portfolio/`; holdings table with card fallback in CSS (`frontend/src/styles.css`)
- [X] T076 [US5] Run T073–T074; fix until passing

**Checkpoint**: Honest current-state analytics

---

## Phase 8: Polish

- [X] T077 [P] Re-run Simulation/Backtest contracts per FR-009 / SC-005
- [X] T078 [P] Frontend `npm test -- --run src/__tests__/portfolio`
- [X] T079 Execute quickstart automated checks in `specs/009-portfolio-capital-allocation/quickstart.md`
- [X] T080 [P] UI review vs `docs/UI_UX_STANDARDS.md` (Simulation obvious, no sandbox copy, 375px, confirm release)
- [X] T081 Mark Feature 009 `DONE` in `docs/ROADMAP.md` after completion checks; do not start Feature 010
- [X] T082 Confirm no credentials/real-money/strategy mutation; no public holdings upsert remains
- [X] T083 Propose commit message (do not auto-commit)

---

## Dependencies

```text
T044–T052 foundation (remove operator holdings API + fill-apply domain)
   │
   ▼
 US1 Simulation Portfolio UI (MVP inspect + fund + warning)
   │
   ├──────────────────► US5 current-state visual
   ▼
 US2 fill hook (catch refuse) + deployed/positions projection
   │
   ├──────────────────► US4 snapshots including simulation_fill (success only)
   └──────────────────► US3 compact allocations (deployed is display-only)
```

## Task Summary

| Metric | Count |
|--------|-------|
| **Correction tasks** | 44 (T044–T087) |
| **Prior superseded delivery** | T001–T043 (not repeated here) |
| **US1** | T053–T058 |
| **US2** | T059–T063, T084–T085 |
| **US3** | T064–T068 |
| **US4** | T069–T072 |
| **US5** | T073–T076 |
| **Setup + Foundational + Polish** | T044–T052, T077–T083 |
| **Convergence** | T086–T087 |

---

## Phase 9: Convergence

- [X] T086 Show per-holding return % when cost basis and value exist, and show average cost and realized P&L when known, on the holdings table and ~375px cards in `frontend/src/features/portfolio/HoldingsPanel.tsx`; keep USDT unrealized/return omitted per FR-001b / US5/AC1 (partial)
- [X] T087 [P] Unit test: with `fillApplyWarning` set, corrupt stored allocation size on load → GET snapshot `warning` is the corrupt-state message (not the fill-apply text), in `backend/tests/unit/test_portfolio_service.py` per spec edge case / data-model warning precedence

