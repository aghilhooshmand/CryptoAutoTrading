# Implementation Plan: Execution Abstraction

**Branch**: `012-execution-abstraction` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 012 — one shared execution contract for Historical,
Simulation, and Real (stub); production Historical and Simulation
**strategy-fill** paths must call through that contract; shared fill economics
and rejection sizing may consolidate; timing, price source, journal wiring,
flatten orchestration, and Portfolio side effects stay mode-specific unless
regressions prove equivalence; Comparison historical fills reuse Backtest’s
Historical path; Real is code/test-only with structured failure
`real_execution_unavailable`; no 003/004 behavior change; no Portfolio on
Backtest; no XT private / operator Real UI.

## Summary

Consolidate duplicated Simulation and Historical fill economics behind one
`ExecutionEngine.execute(ExecutionIntent) → FillResult` contract so Controller
and Risk stay mode-agnostic and Real can attach later. Introduce a
mode-neutral `backend/app/execution/` package: shared intent/result types,
shared buy/sell sizing + reject codes, thin **Historical**, **Simulation**, and
**Real** adapters. Pipelines continue to choose reference prices (next-open vs
live mark), write journals, orchestrate flatten, and apply Simulation-only
Portfolio side effects **outside** the shared economics core. Comparison
already runs Feature 004 `run_engine` — keep that; do not add a Comparison
fill fork. No HTTP/API or operator UI changes. Gate DONE on unchanged
Simulation and Backtest regression outcomes plus a thin Real stub contract
test.

## Technical Context

**Language/Version**: Python 3.12 (backend). No frontend TypeScript work in
scope.

**Primary Dependencies**: Existing FastAPI app modules only for call-site
wiring. Reuse `app.simulation.accounting` (`buy_fill` / `sell_fill` /
`qty_from_notional`), `position_sizing` (`intended_notional` / `is_dust`),
`money.quantize_money`. Today’s duplicated engines:
`SimulationExecutionEngine` (`app.simulation.execution.port`) and
`HistoricalExecutionAdapter` (`app.backtest.execution`). Call sites:
`simulation/pipeline.py`, `simulation/session_service.py` (forced close),
`backtest/engine.py` (strategy fills + `_flatten`), Comparison via
`run_engine`.

**Storage**: N/A — no schema, migrations, or journal format changes.

**Testing**: pytest unit (shared economics parity, Real stub reason + no state
mutation); existing unit/contract suites as behavior gates:
`test_backtest_fills`, `test_backtest_pipeline`, `test_forced_close`, risk
reject/precedence, simulation pipeline/contracts, Portfolio fill-apply.
Optional thin contract test that both adapters implement `ExecutionEngine`.
No Vitest unless an import path accidentally breaks frontend (not expected).

**Target Platform**: Local developer machines (same as Features 003/004)

**Project Type**: Web application backend refactor (`backend/` only for this
feature)

**Performance Goals**: Behavior-preserving; no new latency SLO. Fill path
remains in-process synchronous.

**Constraints**: Spec behavior locks + clarifications (FR-001–FR-017). No
intentional fee/slippage/reason-code renames for Simulation/Backtest. Flatten
orchestration stays mode-owned. Real not selectable in UI. No XT private. No
Risk / Decision Log Mode / History freeze changes. No second trading pipeline.

**Scale/Scope**: Three adapters (Historical, Simulation, Real stub); one shared
economics core; zero new operator screens; Comparison orchestration untouched

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No Risk bypass; Real stub fails closed; no invented fills |
| II Simulation before real money | Pass | Real is stub only; no orders |
| III Single trading pipeline | Pass | Shared execution contract; no second engine |
| IV Controller / Risk authority | Pass | Modes only differ after approval at execution policy |
| V Explicit boundaries | Pass | Mode-specific timing/side effects retained |
| VI Net P&L | Pass | Economics unchanged (behavior lock) |
| VII Traceability | Pass | Journal wiring stays mode-owned; reason codes stable |
| VIII Fail safe | Pass | Real `real_execution_unavailable`; no silent Simulation fallback |
| IX Emergency stop | Pass | Forced-close orchestration unchanged |
| X Intentional simplicity | Pass | Thin adapters + shared math; no new product surface |
| XII Evidence | Pass | Regression gate proves parity |
| XIII–XIV UI | Pass | No UI change; Real not operator-selectable |
| XV Stack | Pass | Python backend only |
| XVI–XVIII Exchange | Pass | No private XT |
| XXVII–XXXI Process | Pass | Spec/plan/tests; roadmap already IN PROGRESS |
| XXXII Execution Abstraction | Pass | This feature implements the constitutional adapter split |
| XXXIV Portfolio | Pass | Backtest/Comparison remain Portfolio-isolated; Simulation apply stays Simulation-only |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design keeps Controller→Risk→Execution→Accounting; shared package owns
fill economics only; Historical next-open and Simulation live marks remain
caller-supplied `reference_price`; Real stub cannot mutate state; Comparison
continues to use Backtest `run_engine` / Historical adapter; no UI Real mode.

## Project Structure

### Documentation (this feature)

```text
specs/012-execution-abstraction/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── call-sites.md        # Fill call-site inventory (not package __init__ comments)
├── contracts/
│   └── execution-contract.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/app/execution/                      # NEW — mode-neutral execution package
├── __init__.py                             # Public exports
├── port.py                                 # ExecutionIntent, FillResult, ExecutionEngine Protocol
├── economics.py                            # Shared buy/sell sizing + reject codes
├── historical.py                           # HistoricalExecutionAdapter (thin)
├── simulation.py                           # SimulationExecutionEngine (thin)
└── real.py                                 # RealExecutionAdapter stub

backend/app/simulation/execution/port.py    # Shim re-exports (compat) OR thin delegate
backend/app/simulation/execution/simulation.py  # Shim if needed
backend/app/backtest/execution.py           # Shim re-export Historical from app.execution

backend/app/simulation/pipeline.py          # Call Simulation adapter via contract; keep journal/Portfolio
backend/app/simulation/session_service.py   # Forced close: keep orchestration; fill via adapter
backend/app/backtest/engine.py               # Strategy fills + flatten via Historical adapter
# comparison/ — no fill changes; already uses run_engine

backend/tests/unit/test_execution_economics.py   # NEW — shared math / reject parity
backend/tests/unit/test_real_execution_stub.py   # NEW — real_execution_unavailable
backend/tests/unit/test_backtest_fills.py        # REGRESSION gate
backend/tests/unit/test_forced_close.py          # REGRESSION gate
# + existing simulation / risk / portfolio fill-apply suites
```

**Structure Decision**: New `backend/app/execution/` package (constitution
XXXII). Runtime Simulation adapter name remains `SimulationExecutionEngine`
(constitution “SimulationExecutionAdapter” is conceptual). Keep **re-export-only**
compatibility shims at historical import paths (zero local fill math). Call-site
inventory lives in `specs/012-execution-abstraction/call-sites.md`. No frontend
or DB changes.

## Complexity Tracking

> No constitution violations requiring justification.
