# Implementation Plan: Controlled Real Execution

**Branch**: `015-controlled-real-execution` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 015 — first Controlled Real (MVP-2) on XT after
Feature 025 / MVP-1 DONE: same session pipeline with explicit Real mode;
confirmed market BUY entries; automatic reducing exits; 50 USDT hard cap;
5-minute pending TTL; XT reconcile (013); dedicated blocked recovery (no 014
auto-resume); RealExecutionAdapter only write path; unmistakable Real UI/API.

## Summary

Enable **Controlled Real** by extending the existing Simulation session worker
and Strategy → Controller → Risk → Execution pipeline with `mode=real`.
Exposure-increasing BUYs pause at a confirmation gate; operator confirm
(within 5 minutes) re-validates safety (incl. XT free USDT) then submits a
**market** order via **RealExecutionAdapter** only. Fills and positions update
only from XT reconcile. Local `startingCapital`/initial cash are **budget
only**, not XT cash. Partial fills record real exposure then block; ≤5s poll
timeout retains order identity and blocks until later reconcile. TP/SL,
reducing SELL, and emergency flatten skip the entry confirmation gate. Real
sessions never mutate Simulation Portfolio holdings. Restart → Real
`RECOVERY_BLOCKED` with discarded pendings and **no** auto-resume.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript/React (frontend)

**Primary Dependencies**: FastAPI session API + Simulation worker/pipeline
(003/010/011/014/025); Execution protocol (012); XT private client + signing
(013); SQLAlchemy/SQLite; Strategy registry (005/006/025 TP/SL)

**Storage**: Extend `SimulationSessionRow` for Real mode fields + pending
confirmation; optional `PendingEntryConfirmation` / Real order reconcile
rows; **no** Simulation Portfolio writes for Real fills

**Testing**: pytest unit/contract with XT fakes (place ack ≠ fill; reject;
timeout; TTL expiry; confirm-time fail; blocked recovery; Portfolio
isolation); frontend Real mode / confirm UI smoke ~375px; optional live smoke
gated on credentials

**Target Platform**: Local operator machines (same as Features 003–014)

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Keep ~2s Simulation worker class; Real place+poll budget
≤5s; on timeout enter unsettled/blocked (retain order) — do not invent fill

**Constraints**: Spec FR-001–FR-011 + Clarifications Q1–Q5 + analyze I1–I4
(FR-004a/b, FR-006b/c); constitution I–V, VII–IX, XIII–XV, XVII–XVIII, XXXII,
XXXIV; market orders only; allocated ≤ 50 USDT; XT free gate on entry; budget
≠ XT cash; no autonomous Real entries; no 014 Sim auto-recovery for Real; no
Portfolio redesign; no Torque/GE

**Scale/Scope**: One Real session shape (one pair, one long); confirmation
gate; RealExecutionAdapter XT write; Real blocked recovery; minimal UI/API
distinctness

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Confirm gate; 50 USDT cap; fail closed; no invented fills |
| II Simulation before real | Pass | MVP-1 / 025 done; Controlled Real only (confirmed entries) |
| III Single pipeline | Pass | Same session/pipeline; mode-specific Execution/accounting |
| IV Controller / Risk | Pass | Confirm only after Controller+Risk; re-validate on confirm |
| V Explicit boundaries | Pass | Cap, one position, duration/stops unchanged pattern |
| VI Net P&L | Pass | Fees from XT reconcile / known economics; no optimistic P&L |
| VII Traceability | Pass | Real provenance; pending/confirm/reconcile journals |
| VIII Fail safe | Pass | Ack ≠ fill; unclear → unsettled/fail closed |
| IX Emergency stop | Pass | Flatten without entry confirm when safe |
| X Intentional simplicity | Pass | Market only; no limit; no autonomy |
| XI Conventional strategies | Pass | Existing strategies; no Real-only strategy engine |
| XII Evidence | Pass | FR-010 + quickstart + MVP-2 validation |
| XIII–XIV UI | Pass | Unmistakable Real; no Portfolio redesign |
| XV Stack | Pass | Existing Python + React |
| XVII–XVIII XT | Pass | Private writes only via Real adapter; signing from 013 |
| XXXII Execution | Pass | RealExecutionAdapter completes 012 stub |
| XXXIV Portfolio | Pass | Real MUST NOT write Sim Portfolio holdings |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design reuses session/pipeline, Confirmation gate as Execution-stage
pause (not a second engine), RealExecutionAdapter as sole XT write path,
013 for reconcile reads, and dedicated Real blocked recovery that explicitly
does **not** reuse 014 auto-resume. See [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/).

## Project Structure

### Documentation (this feature)

```text
specs/015-controlled-real-execution/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── session-real-api.md
│   ├── confirmation-gate.md
│   ├── real-execution-adapter.md
│   └── real-blocked-recovery.md
├── spec.md
└── checklists/
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/simulation.py              # Real mode create + confirm/decline
│   ├── execution/
│   │   ├── real.py                    # RealExecutionAdapter (live)
│   │   └── port.py                    # intent extensions if needed
│   ├── xt_account/
│   │   └── client.py                  # signed POST market order (+ keep GETs)
│   ├── simulation/
│   │   ├── session_service.py         # mode=real validation; no Portfolio write
│   │   ├── pipeline.py                # confirmation gate; Real adapter branch
│   │   ├── recovery.py                # Real: never auto-resume
│   │   └── pending_confirmation.py    # TTL / discard / confirm re-validate
│   └── db/models.py                   # pending + Real order fields
└── tests/
    ├── unit/                          # gate, TTL, adapter, recovery, isolation
    └── contract/                      # Real session API + confirm routes

frontend/
├── src/features/simulation/           # Real mode, confirm UI, blocked banner
└── src/services/simulationApi.ts
```

**Structure Decision**: Extend existing `backend/` + `frontend/` web app. No
new top-level package. XT write methods live on `XtPrivateClient` but are
**only** callable from RealExecutionAdapter (tests enforce no public
fund-movement HTTP routes beyond controlled session confirm path).

## Complexity Tracking

> No unjustified constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
