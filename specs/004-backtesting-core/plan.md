# Implementation Plan: Backtesting Core

**Branch**: `004-backtesting-core` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)
 
**Input**: Feature specification from `/specs/004-backtesting-core/spec.md`  
(including Session 2026-08-11 clarifications)

## Summary

Deliver **deterministic historical backtesting** under Auto Trading: load
normalized closed candles for a pair/timeframe/window, walk them
chronologically with the **shared** Dual EMA(9)/EMA(21), Controller, Risk, and
accounting modules, then fill via a **backtest-specific HistoricalExecutionAdapter**
(next-open strategy fills; final-close flatten — not live simulation execution).
Persist ≤**20** completed and ≤**5** failed runs; expose drawdown and
warm-up-independent buy-and-hold. No real orders, WebSockets, or strategy
optimization.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + Uvicorn + httpx (existing); SQLAlchemy 2.x
+ SQLite (existing Feature 003); Vite + React Router + Lucide (existing).
Reuse Feature 003 modules (`strategy.dual_ema`, `control`, `accounting`,
`position_sizing`, `money`). Feature 004 adds `HistoricalExecutionAdapter`
for historical fills — do **not** route through live `execution.simulation`.
No WebSockets. No XT private SDKs.

**Storage**: SQLite (same `SIMULATION_DB_PATH` / `backend/data/` family or
dedicated `backtest.db` — see research Decision 6). FIFO **20** completed +
FIFO **5** failed runs.

**Testing**: pytest (unit: next-open fills, end-close flatten, drawdown,
round-trip win/loss, warm-up-independent B&H, history-cap reject, empty and
fewer-than-21 `insufficient_history`, FIFO 5 failed, `approved_unexecutable`
vs `rejected`, determinism; contract: `/backtest` API; integration: fixture
candles through shared pipeline + historical adapter). Vitest + RTL for Auto
Trading backtest UI (~375px).

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
  (constitution V 1.2.0 historical-backtest exception)
- Reject oversized history before accept (no silent truncate; no run row)
- Fewer than 21 closed candles after fetch → `insufficient_history` (failed row
  if already `running`); ≥21 → HOLD through EMA warm-up
- Persist ≤20 completed runs; ≤5 failed runs (FIFO); survive restart; inspect + delete
- Post-accept fetch/execution failures persist `failed`; pre-accept validation does not
- Max one in-flight backtest at a time; **synchronous** execution under cap (v1)
- Approved-but-unexecutable (`no_next_candle`) distinct from risk `rejected`
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
| III–IV Pipeline / controller–risk | Pass | Shared Dual EMA advisory; Controller + Risk before historical execution adapter |
| V Explicit session boundaries | Pass | Constitution V historical-backtest exception (1.2.0): window replaces duration; optional profit/loss/max_trades for offline backtests only; capital nesting + timeframe required; Feature 003/live unchanged |
| VI Net P&L | Pass | Fees/slippage; liquidation-consistent equity for drawdown/early exits |
| VII Decision traceability | Pass | Persist decisions + trades per completed run |
| VIII Fail safe | Pass | Reject missing/empty/<21-candle/oversized history; HOLD only during warm-up on valid ≥21 windows; no invented candles |
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

Re-evaluated after analyze remediations (constitution V 1.2.0 exception,
FR-003 HistoricalExecutionAdapter wording, warm-up <21 fail / ≥21 HOLD,
failed persistence rules): still **PASS**. Shared Dual EMA / control / risk /
accounting; fills isolated in HistoricalExecutionAdapter; Feature 002 range
fetch only; FIFO 20 completed + FIFO 5 failed; `approved_unexecutable` ≠
`rejected`.

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
│   │   ├── engine.py                # chronological walk; wires shared pipeline
│   │   ├── execution.py             # HistoricalExecutionAdapter (next-open / end-close)
│   │   ├── metrics.py               # drawdown, round-trips, B&H (window-based)
│   │   ├── limits.py                # max candle / span caps
│   │   ├── repository.py            # SQLite CRUD + FIFO 20 completed / 5 failed
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
that **imports** Feature 003 strategy/control/risk/accounting/sizing/money —
never copies Dual EMA — and owns `HistoricalExecutionAdapter` for fills.
Extend Feature 002 market-data range fetch at the adapter boundary only.
Frontend adds `features/backtest/` under Auto Trading.

## Complexity Tracking

> No constitution violations requiring justification.
