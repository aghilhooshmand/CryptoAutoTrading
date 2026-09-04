# Implementation Plan: Torque Trading Program Core

**Branch**: `016-torque-trading-program` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature 016 — call FORGE `torque.check` for phenotype form; bind
existing strategy registry leaves + AND/OR/vote composition in this repo;
evaluate via deterministic Backtest (optional Simulation later); expose
`evaluate` metrics for Feature 019 UGE. Simulation/Backtest only; no Real;
no FORGE source copy. FORGE path:
`/home/aghil/Documents/my document/limerick/projects/FORGE`.

## Summary

Add a thin `backend/app/torque_bind/` (name may vary) package that:

1. Calls `from torque import check` (editable FORGE install).
2. Maps a well-formed `Program` tree onto existing `Strategy` instances
   (leaves = registry ids such as `rsi`, `macd`, `dual_ema`) plus composition
   instructions `and` / `or` / `vote`.
3. Runs composed signals through Feature **004** `run_engine` on fixed
   candles → metrics for UGE fitness (019).

Do not fork Torque. Do not put strategies into FORGE. Do not touch
RealExecutionAdapter. Prefer Backtest for MVP evaluate (deterministic);
Simulation wiring is allowed but **not** required for 016 DONE. Optional HTTP
smoke is **not** required for DONE when Python `evaluate_phenotype` + tests
pass.

## Technical Context

**Language/Version**: Python 3.12 (backend). Optional thin FastAPI routes or
CLI for smoke; frontend UI not required for MVP.

**Primary Dependencies**: FORGE editable `torque` (language only API used);
existing `app.strategy.registry`, `app.backtest.engine.run_engine`,
Controller/Risk via Backtest path; httpx unused for FORGE.

**Storage**: N/A for MVP — evaluate is request/in-process. Optional later
persist of phenotype strings (not required for 016 DONE).

**Testing**: pytest unit (check→bind, composition semantics, unknown leaf
fail-closed); Backtest fixture replay for SC-002/SC-003; import guard that
`torque_bind` does not import `app.execution.real` place path; no live Kraken
keys.

**Target Platform**: Local developer machines (same as Features 003/004)

**Project Type**: Web application backend feature (`backend/`); docs under
`specs/016-torque-trading-program/`

**Performance Goals**: Single phenotype Backtest on fixture candles completes
in developer-interactive time (no hard SLO); UGE scale deferred to 019.

**Constraints**: Constitution XXXV–XXXVII; FR-001–FR-009; no Real orders; no
copy/vendor FORGE; composition = agreement-style signals only; keyword params
MUST match existing ParamDef names (`period`, `fastPeriod`, …).

**Scale/Scope**: ≥2 strategy leaves + 3 composition ops; one evaluate entry
point; minimal optional HTTP/CLI; no UGE engine in 016.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No Real; Risk still on Backtest path |
| II Simulation before real | Pass | Sim/Backtest only; 015 paused |
| III Single pipeline | Pass | Composed Strategy → same Controller/Risk/Execution |
| IV Controller / Risk | Pass | No bypass |
| V Explicit boundaries | Pass | FORGE = form; this repo = meaning |
| VI Net P&L | Pass | Backtest fees/slippage unchanged |
| VII Traceability | Pass | Phenotype source + metrics returned |
| VIII Fail safe | Pass | Invalid form / unknown leaf fail closed |
| X Intentional simplicity | Pass | Thin bind layer; reuse registry + run_engine |
| XII Evidence | Pass | Fixture Backtest gates |
| XV Stack | Pass | Python + editable FORGE |
| XVI–XVIII Exchange | Pass | No private trading from 016 |
| XXXV Torque layer | Pass | Call FORGE torque; no second engine |
| XXXVI GE | Pass | evaluate surface only; UGE in 019 |
| XXXVII Fitness | Pass | Metrics explicit for later fitness |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design keeps `torque.check` outside trading semantics; composite
`Strategy` still emits `StrategySignal` into Backtest’s existing
Controller→Risk→Execution path; Real adapter untouched; FORGE not vendored.

## Project Structure

### Documentation (this feature)

```text
specs/016-torque-trading-program/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── torque-bind-api.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/app/torque_bind/
├── __init__.py
├── catalogue.py          # leaf + composition ParamSpec / name map
├── bind.py               # Program → Strategy (composite)
├── compose.py            # and / or / vote signal combinators
├── evaluate.py           # phenotype + candles/config → metrics
└── errors.py             # stable bind/evaluate error codes

backend/app/api/          # optional thin routes (e.g. /torque/check, /torque/evaluate)
backend/tests/unit/test_torque_bind_*.py
backend/tests/integration/test_torque_backtest_evaluate.py

docs/FORGE_INTEGRATION.md  # already present — install path
```

**Structure Decision**: Backend-only bind package under `app/torque_bind/`.
Reuse `app.strategy` and `app.backtest`; do not add a parallel engine. Optional
minimal API for operator smoke; UGE will call Python `evaluate` in 019.

## Complexity Tracking

> No constitution violations requiring justification.
