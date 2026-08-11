# Implementation Plan: Backtesting Core

**Branch**: `004-backtesting-core` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-backtesting-core/spec.md`  
(including Session 2026-08-11 clarifications)

## Summary

Deliver **deterministic historical backtesting** under Auto Trading: load
normalized closed candles for a pair/timeframe/window, walk them
chronologically with the **shared Dual EMA(9)/EMA(21)** strategy, route
signals through the same Controller → Risk → Simulation execution path as
Feature 003, fill approved strategy trades at **Candle N+1 open** (fee +
adverse slippage), flatten open longs at end using **final close**, persist
up to **20** completed runs (config, summary, trades, decisions) in SQLite,
and expose inspectable results including liquidation-path max drawdown and
cost-aware buy-and-hold comparison. No real orders, WebSockets, or strategy
optimization.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + Uvicorn + httpx (existing); SQLAlchemy 2.x
+ SQLite (existing Feature 003); Vite + React Router + Lucide (existing).
Reuse Feature 003 simulation modules (`strategy.dual_ema`, `control`,
`accounting`, `position_sizing`, `execution.simulation`, `money`). No
WebSockets. No XT private SDKs.

**Storage**: SQLite (same `SIMULATION_DB_PATH` / `backend/data/` family or
dedicated `backtest.db` under `backend/data/` — see research Decision 6).
Tables for runs, trades, decisions; FIFO retention of 20 completed runs.

**Testing**: pytest (unit: next-open fills, end-close flatten, drawdown from
per-candle equity, round-trip win/loss, buy-and-hold, history-cap reject,
determinism; contract: `/backtest` API; integration: fixture candles through
full pipeline). Vitest + RTL for Auto Trading backtest configure/run/list/
inspect (~375px).

**Target Platform**: Local developer machines via browser; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Local operator scale. A max-sized run (≤ documented
candle cap) completes within tens of seconds on a developer machine; UI
remains usable (list/summary) without multi-second freezes for typical
stored journals.

**Constraints**:
- Historical evaluation only; no private XT APIs; no real orders; no credentials
- Shared Dual EMA only — no duplicate strategy module
- Long-only single full position; Feature 003 sizing + fee/slippage defaults
- Strategy signal on closed Candle N; fill reference = N+1 **open**; no N+1 →
  no strategy fill; end-of-run flatten uses final processed **close**
- Optional `max_trades`, optional profit/loss rates; required capital nesting
- Reject oversized history before run (no silent truncate)
- Persist ≤20 completed runs; survive restart; inspect + delete
- Max one in-flight backtest at a time (v1)
- Market data only via Feature 002 normalized boundary (extend range fetch)
- No WebSockets, shorts, leverage, optimization, ML, sentiment, real money

**Scale/Scope**: Single local operator; Auto Trading hosts UI; SQLite local
file; history capped (see research Decision 4)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Capital nesting; optional early exits; fail-safe on missing/oversized history |
| II Simulation before real money | Pass | Backtest is offline simulated fills only; real money unavailable |
| III–IV Pipeline / controller–risk | Pass | Shared Dual EMA advisory; Controller + Risk before sim execution |
| V Explicit session boundaries | Pass | Window + capital nesting required; optional max_trades / profit / loss; backtest is historical evaluation (not a live wall-clock session) — duration replaced by start/end |
| VI Net P&L | Pass | Fees/slippage; liquidation-consistent equity for drawdown/early exits |
| VII Decision traceability | Pass | Persist decisions + trades per completed run |
| VIII Fail safe | Pass | Reject missing/insufficient/oversized history; no invented candles |
| IX Emergency stop | Pass N/A for offline batch | Live emergency stop remains Feature 003; backtest is not a live session (cancel in-flight optional polish) |
| X Intentional simplicity | Pass | One strategy; reuse 003 domain; sync run under cap; 20-run retention |
| XI Conventional strategies | Pass | Dual EMA only |
| XII No guaranteed profit | Pass | Results are historical evidence; UI must not imply future profit |
| XIII Three primary UI areas | Pass | Under Auto Trading; no fourth primary nav |
| XIV Responsive UX | Pass | Primary controls usable at ~375px |
| XV Python / React / SQL | Pass | SQLite for completed runs |
| XVI–XVIII Adapter / credentials | Pass | Feature 002 boundary only; no trading credentials |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Plan encodes trading-critical + determinism tests |
| XXX Git commit traceability | Pass | Propose commit message; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

Re-evaluated after `research.md`, `data-model.md`, `contracts/`, and
`quickstart.md`: still **PASS**. Shared Dual EMA + accounting/risk reused;
next-open / end-close fill rules isolated in backtest engine; market range
fetch stays behind Feature 002 adapter; XT strings do not enter backtest
domain contracts; SQLite retention FIFO of 20 completed runs.

## Project Structure

### Documentation (this feature)

```text
specs/004-backtesting-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── backtest-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   └── backtest.py              # /backtest/* routes
│   ├── market_data/
│   │   ├── service.py               # extend get_candles range/pagination
│   │   ├── adapters/base.py         # optional start/end params
│   │   └── adapters/xt_spot.py      # XT startTime/endTime + page loop
│   ├── simulation/                  # Feature 003 — reuse, do not fork Dual EMA
│   │   ├── strategy/dual_ema.py
│   │   ├── control/
│   │   ├── accounting.py
│   │   ├── position_sizing.py
│   │   ├── execution/
│   │   └── money.py
│   ├── backtest/                    # Feature 004 domain
│   │   ├── __init__.py
│   │   ├── engine.py                # chronological walk, next-open fills
│   │   ├── metrics.py               # drawdown, round-trips, B&H
│   │   ├── limits.py                # max candle / span caps
│   │   ├── repository.py            # SQLite CRUD + FIFO 20
│   │   └── service.py               # validate, run, list, get, delete
│   ├── db/
│   │   └── models.py                # add backtest tables
│   └── main.py                      # mount router
└── tests/
    ├── unit/
    │   ├── test_backtest_fills.py
    │   ├── test_backtest_metrics.py
    │   ├── test_backtest_limits.py
    │   └── test_backtest_determinism.py
    ├── contract/
    │   └── test_backtest_api.py
    └── integration/
        └── test_backtest_pipeline.py

frontend/
├── src/
│   ├── pages/AutoTradingPage.tsx    # host simulation + backtest sections
│   ├── features/backtest/
│   │   ├── BacktestConfigForm.tsx
│   │   ├── BacktestResultsPanel.tsx
│   │   ├── BacktestRunList.tsx
│   │   ├── BacktestTrades.tsx
│   │   ├── BacktestDecisions.tsx
│   │   └── useBacktest.ts
│   ├── services/backtestApi.ts
│   └── __tests__/
│       └── backtest*.test.tsx
```

**Structure Decision**: Keep dual-package layout. Add `backend/app/backtest/`
that **imports** Feature 003 strategy/control/accounting/execution — never
copies Dual EMA. Extend Feature 002 market-data range fetch at the adapter
boundary only. Frontend adds `features/backtest/` under Auto Trading.

## Complexity Tracking

> No constitution violations requiring justification.
