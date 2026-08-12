# Implementation Plan: Strategy Comparison and Evaluation

**Branch**: `007-strategy-comparison` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-strategy-comparison/spec.md`  
(including Session 2026-08-12 clarifications)

## Summary

Add **fair multi-strategy comparison** under Auto Trading: one shared
historical window and money/risk assumptions, **2–5 legs** (each a registered
strategy + its own params), **one candle fetch**, then each leg runs through
the existing Feature 004 `run_engine` path as a normal backtest run marked
`origin=comparison`. Return a synchronous comparison summary (no “best”
badge). Drill-down reuses Feature 004 inspect APIs; main backtest history
hides comparison-originated runs by default. No optimization, ML, or real money.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: Existing FastAPI + SQLAlchemy + SQLite; Vite + React.
Reuse `app.backtest.engine.run_engine`, `app.backtest.service` candle fetch /
validation patterns, `app.strategy.registry.validate_and_materialize`,
`StrategyConfigFields`. New comparison API + orchestrator only — no second
strategy or accounting implementation.

**Storage**: Extend SQLite schema: comparison header + leg rows; add
`origin` (+ optional `comparison_id`) on `BacktestRunRow` (or equivalent) so
legs are filterable. Retention: **10** completed + **5** failed comparisons
(FIFO). Leg runs keep Feature 004 **20** completed + **5** failed FIFO.

**Testing**: pytest unit (orchestrator: shared candles, max/min legs, strictest
`S`, fail-closed on leg failure, retention); contract (`POST` comparison,
list/get, history filter); integration (two strategies same fixture →
deterministic metrics). Vitest: multi-leg form, results table without winner
badge, default hide comparison runs in history.

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Synchronous comparison of ≤5 legs on ≤5000 candles;
soft goal tens of seconds on a developer machine (same spirit as Feature 004).
No dedicated SLO gate.

**Constraints**:
- Reuse Feature 004 engine + Feature 005/006 registry only
- Sync: one fetch, all legs, final state in one response
- 2–5 legs; duplicate strategy ids allowed with different params
- Strictest-leg `min_history_candles` gate; oversized reject pre-accept
- Fail-closed if any leg fails after accept (no partial leaderboard)
- No automatic “best/winner” labeling
- No optimization / grid / ML / walk-forward / real money / WebSockets
- Auto Trading only (constitution XIII)
- Comparison-originated runs hideable from default backtest history

**Scale/Scope**: Local single operator; ≤5 legs; ≤10 stored completed
comparisons

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Shared nesting + optional Feature 004 risk limits |
| II Simulation before real money | Pass | Historical evaluation only |
| III–IV Pipeline / controller–risk | Pass | Per-leg `run_engine` unchanged |
| V Explicit session boundaries | Pass | Historical-backtest exception; shared optional limits |
| VI Net P&L | Pass | Engine summaries include fees/slippage |
| VII Decision traceability | Pass | Per-leg journals via existing backtest tables |
| VIII Fail safe | Pass | Pre-accept rejects; fail-closed comparison |
| IX Emergency stop | Pass | N/A (offline); no new live controls |
| X Intentional simplicity | Pass | Thin orchestrator over existing engine |
| XI Conventional strategies | Pass | Registry strategies only; no ML |
| XII Evidence, not guarantees | Pass | No winner badge; no profit guarantees |
| XIII Three primary UI areas | Pass | Auto Trading only |
| XIV Responsive UX | Pass | Table + existing inspect panels |
| XV Python / React / SQL | Pass | SQLite migration for comparison + origin |
| XVI–XVIII Adapter / credentials | Pass | Public candles via existing market service |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Contracts + golden shared-fixture tests |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Design adds comparison tables, an
`origin` mark on backtest runs, and a sync orchestrator that calls
`run_engine` per leg; Controller/Risk/Execution and strategy modules stay
unchanged; no ranking or real-money path.

## Project Structure

### Documentation (this feature)

```text
specs/007-strategy-comparison/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── strategy-comparison-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   └── comparison.py            # NEW — POST/GET/list/delete comparisons
│   ├── backtest/
│   │   ├── engine.py                # REUSE run_engine (no strategy fork)
│   │   ├── service.py               # EXTRACT/reuse candle fetch + validate helpers
│   │   └── repository.py            # EXTEND list filter by origin
│   ├── comparison/                  # NEW package
│   │   ├── service.py               # Sync orchestrator
│   │   ├── repository.py            # Comparison retention 10/5
│   │   └── metrics.py               # Map engine summary → comparison row (+ vs B&H)
│   ├── db/models.py                 # ADD Comparison* + BacktestRunRow.origin
│   └── main.py                      # Mount comparison router
└── tests/
    ├── unit/test_comparison_*.py
    ├── contract/test_comparison_api.py
    └── integration/test_comparison_shared_candles.py

frontend/
├── src/
│   ├── features/comparison/         # NEW form, results table, list
│   ├── features/backtest/           # EXTEND list default filter origin≠comparison
│   ├── pages/AutoTradingPage.tsx    # Host comparison section
│   ├── services/comparisonApi.ts    # NEW
│   └── __tests__/comparison*.test.tsx
└── ...
```

**Structure Decision**: Extend existing backend/frontend app. New thin
`comparison` package + API; reuse backtest engine and strategy registry. No
new primary nav area.

## Complexity Tracking

> No constitution violations requiring justification.
