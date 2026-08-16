# Implementation Plan: Live Paper-Trading Hardening

**Branch**: `014-live-paper-trading-hardening` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 014 — harden existing live-market Simulation /
paper-trading for restart recovery, reconciliation, fail-closed
`RECOVERY_BLOCKED`, duplicate-event prevention, skip offline candles, stale-mark
policy, bounded public market retries, Portfolio consistency, emergency stop
under degradation, operator-visible status (~375px). Reuse single pipeline;
no second paper engine; no Real trading / RealExecutionAdapter / private XT
trading.

## Summary

Extend Simulation recovery so backend restart **reconciles** orphaned sessions
and **conditionally auto-resumes** only when FR-006 gates pass; otherwise enter
non-trading **`RECOVERY_BLOCKED`**. Skip offline closed candles by advancing
`last_processed_candle_open_time` with an audit record. Strengthen
watermark/journal idempotency and add bounded public market-data retries (max 1,
0.5s / ≤2s Retry-After). Keep Controller/Risk/Simulation Portfolio authority;
expose resume + clearer UI/status. Do not invent prices, fills, or balances.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript/React (frontend)

**Primary Dependencies**: Existing FastAPI Simulation stack; SQLAlchemy/SQLite;
public `market_data` / `XtSpotAdapter`; Feature 009 Portfolio; Feature 012
SimulationExecutionAdapter (unchanged fill path)

**Storage**: Existing Simulation SQLite schema — extend session state enum /
columns for recovery reasons + skipped-gap audit; strengthen journal uniqueness

**Testing**: pytest unit (reconcile gates, recovery outcomes, watermark skip,
retry bounds, state machine) + contract/API (`resume`, recovery status) +
frontend status/`RECOVERY_BLOCKED` tests; fixture clocks — no multi-hour live CI

**Target Platform**: Local operator machines (same as Features 003–013)

**Project Type**: Web application (`backend/` + `frontend/` Auto Trading UI)

**Performance Goals**: Startup recovery completes before worker ticks invent
work; public retry wait capped at 2s; worker poll remains ~2s class

**Constraints**: Spec FR-001–FR-020 + clarifications; constitution I, III, IV,
VIII, IX, XXXII, XXXIV; no RealExecutionAdapter; no private trading APIs; no
4th primary nav; History `STOPPED` remains terminal

**Scale/Scope**: One Simulation pipeline; one new lifecycle state; one resume
endpoint; reconcile module; public retry wrapper; status UI updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Fail closed; never invent; gates before resume |
| II Simulation before real money | Pass | Paper only; Real path untouched |
| III Single trading pipeline | Pass | Harden in place; no second engine |
| IV Controller / Risk authority | Pass | Strategies advisory; Risk stale rejects retained |
| V Explicit boundaries | Pass | Existing session risk/stop controls kept |
| VI Net P&L | Pass | No invented economics on recovery |
| VII Traceability | Pass | Journals + skipped-gap audit + recovery codes |
| VIII Fail safe | Pass | `RECOVERY_BLOCKED`; unsafe mark / unflattened |
| IX Emergency stop | Pass | Available in degraded / `RECOVERY_BLOCKED` |
| X Intentional simplicity | Pass | Extend recovery/state machine; thin retry |
| XII Evidence | Pass | FR-020 test list |
| XIII Primary product areas | Pass | Auto Trading only; no 4th nav |
| XIV Operator UI | Pass | Distinguish `RECOVERY_BLOCKED` vs `STOPPED`; ~375px |
| XV Stack | Pass | Existing Python + React |
| XVI–XVII Exchange adapters | Pass | Public market only; private unused for fills |
| XVIII Credential safety | Pass | No new secrets; public retries only |
| XXXII Execution abstraction | Pass | Simulation adapter only; Real stays unavailable |
| XXXIV Portfolio | Pass | Simulation Portfolio reconcile; Real XT isolated |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design reuses Simulation worker/pipeline/Risk/Portfolio; adds reconcile +
`RECOVERY_BLOCKED` + resume; public retries are read-only and bounded; skip
policy never invents fills; RealExecutionAdapter and XT private trading remain
out of scope. See [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/).

## Project Structure

### Documentation (this feature)

```text
specs/014-live-paper-trading-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── simulation-recovery-api.md
│   └── public-market-retry.md
├── spec.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks — not created by this command
```

### Source Code (repository root)

```text
backend/app/simulation/
├── recovery.py              # recover-and-reconcile (replace orphan→STOPPED-only)
├── reconcile.py             # NEW: FR-006 gates → ReconcileResult
├── state_machine.py         # add RECOVERY_BLOCKED transitions
├── gap_skip.py              # NEW: offline gap detect + watermark advance + audit
├── pipeline.py              # idempotent candle handling; entry block while unsafe
├── worker.py                # ignore non-RUNNING; ensure no trade in RECOVERY_BLOCKED
├── session_service.py       # resume_session; stop from RECOVERY_BLOCKED; status fields
└── control/risk.py          # keep UNSAFE_QUOTE_LIMIT=3; entry block clarity

backend/app/market_data/
├── public_retry.py          # NEW: bounded public read retry (R5)
└── adapters/xt_spot.py      # remains thin; Simulation uses public_retry helper

backend/app/api/
└── simulation.py            # POST .../resume; status includes recovery fields

backend/app/db/
└── models.py                # state; recovery_reason; skipped_gap table/columns;
                             # journal uniqueness

frontend/src/features/simulation/
├── SessionStatusPanel.tsx   # RECOVERY_BLOCKED + recovery reasons + Resume
├── SimulationHistoryList.tsx
├── useSimulationSession.ts
└── simulationApi.ts         # resumeSession()

backend/tests/
├── unit/test_reconcile.py
├── unit/test_recovery_014.py
├── unit/test_gap_skip.py
├── unit/test_public_market_retry.py
├── unit/test_state_machine.py          # extended
└── contract/test_simulation_resume_api.py
```

**Structure Decision**: Extend existing Simulation + public market_data packages;
no new trading engine or private XT usage for paper fills.

## Complexity Tracking

> No constitution violations requiring justification.
