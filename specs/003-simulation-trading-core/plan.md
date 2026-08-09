# Implementation Plan: Simulation Trading Core

**Branch**: `003-simulation-trading-core` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-simulation-trading-core/spec.md`  
(including Session 2026-08-09 clarifications and locked planning decisions below)

## Summary

Deliver the first end-to-end **simulation-only** trading machine on Auto Trading:
consume Feature 002 normalized market data, evaluate a **dual EMA(9)/EMA(21)
crossover** once per newly **closed** candle, route every signal through
Trading Controller → Risk Manager → **Simulation** execution, persist session +
Decision/Trade journals in **SQLite**, enforce Session **NET P&L** hard limits
using **liquidation equity** while LONG (hypothetical adverse SELL with
fee/slippage; raw MTM remains informational), and never place real XT orders
or call private APIs. At most one active session; backend restart must not
silently resume execution.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + Uvicorn + httpx (existing); **SQLAlchemy 2.x**
+ stdlib **sqlite3** driver for domain persistence; Vite + React Router + Lucide
(existing). No WebSockets. No XT private SDKs.

**Storage**: **SQLite** file for simulation domain state (sessions, balances/
positions snapshot fields, Decision Journal, Trade Journal, candle-progress
cursor). Path via env (default under `backend/data/`). Feature 002
`localStorage` prefs remain UI-only and are not reused for trading domain
records.

**Testing**: pytest (unit: accounting incl. liquidation vs mark equity and
no double-count of exit costs, EMA/crossover, state machine, clock,
duplicate-candle guard, risk rejects, max_trades + forced close; contract:
simulation HTTP API; integration: pipeline with fake market data + fake clock).
Vitest + RTL for Auto Trading configure/start/status/stop/emergency-stop and
simulation labeling (~375px).

**Target Platform**: Local developer machines via browser; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Local operator scale only. Closed-candle evaluation loop
MUST detect a newly closed bar and complete one pipeline pass promptly enough
for demo/acceptance (order of seconds after close, not sub-ms HFT). Session
status/journals readable without multi-second UI freezes on typical journal
sizes for one session.

**Constraints**:
- Simulation only; no private XT APIs; no real orders; no credentials
- Long-only single full position; BUY only from FLAT; SELL only full close
- Dual EMA crossover only; evaluate once per newly closed candle; no duplicate
  processing of the same candle
- Controller + Risk mandatory before any simulated fill
- Defaults: fee **0.10%** / adverse slippage **0.05%** per fill side; overridable
- Session limits on **liquidation** Session NET P&L while LONG (mark equity informational)
- `max_trades` caps strategy-driven fills; one forced safety close may exceed `trade_count` by one
- Hard-stop flatten only with safe price; else fail-safe unflattened
- Market data only via Feature 002 normalized boundary
- No WebSockets, shorts, leverage, multi-session, multi-strategy, ML,
  sentiment/news, backtesting, production deploy
- `ExecutionEngine` port with simulation implementation only; reject real_money at API (no real XT engine in 003)

**Scale/Scope**: Single local operator; one simulation session; Auto Trading
primary UI; optional thin Portfolio read of recent simulation summary; SQLite
local file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Hard limits, emergency stop, fail-safe, long-only bounds |
| II Simulation before real money | Pass | Simulation only; real-money unavailable/non-startable |
| III–IV Pipeline / controller–risk authority | Pass | Strategy advisory; Controller + Risk before SimulationExecution |
| V Explicit session boundaries | Pass | All FR-005 bounds required to start |
| VI Net P&L | Pass | Hard limits use liquidation equity − start equity while LONG; fees/slippage in hyp. eval and actual fills once |
| VII Decision traceability | Pass | Decision Journal (HOLD/approve/reject) + Trade Journal |
| VIII Fail safe | Pass | Stale/unsafe data rejects; no invented exit on hard stop |
| IX Emergency stop | Pass | Immediate halt of new execution + stop path |
| X Intentional simplicity | Pass | One strategy, one session, SQLite, injectable clock; no unused real-money engine module |
| XI Conventional strategies | Pass | Dual EMA crossover only |
| XII No guaranteed profit | Pass | Simulation evidence only; UI must not imply guarantees |
| XIII Three primary UI areas | Pass | Auto Trading extended; Portfolio optional thin summary only |
| XIV Responsive UX | Pass | Primary controls usable at ~375px |
| XV Python / React / SQL | Pass | SQLite introduced for domain journals/sessions |
| XVI–XVIII Adapter / credentials / withdrawals | Pass | Consume Feature 002 market boundary; no trading credentials; no withdrawals |
| XIX–XXVI Sentiment | Pass | Out of scope (no sentiment trading or Dashboard sentiment work here) |
| XXVII–XXIX Spec-driven / tests / source of truth | Pass | Plan encodes tests for trading-critical paths |
| XXX Git commit traceability | Pass | Propose commit message; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

Re-evaluated after `research.md`, `data-model.md`, `contracts/`, and
`quickstart.md` (including liquidation-equity hard limits and max_trades
clarification): still **PASS**. Simulation execution is isolated behind an
`ExecutionEngine` port with **only** a simulation implementation; real-money
mode is rejected at the API/session boundary with no XT execution module in
this feature; SQLite holds only simulation domain records; market data stays
behind Feature 002 normalized APIs/services with no XT payload leakage into
strategy/risk/simulation code.

## Project Structure

### Documentation (this feature)

```text
specs/003-simulation-trading-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── simulation-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                 # add sqlalchemy
├── data/                          # default SQLite location (gitignored)
├── app/
│   ├── main.py                    # lifespan: DB init + recover orphan sessions
│   ├── db/
│   │   ├── session.py             # engine, session factory, SIMULATION_DB_PATH
│   │   └── models.py              # SQLAlchemy tables
│   ├── api/
│   │   ├── health.py
│   │   ├── market_data.py         # unchanged Feature 002
│   │   └── simulation.py          # /simulation/* routes
│   ├── market_data/               # Feature 002 — consume only public models/service
│   ├── simulation/                # Feature 003 domain (sim-only)
│   │   ├── __init__.py
│   │   ├── clock.py               # Clock protocol, SystemClock, FakeClock
│   │   ├── money.py               # decimal helpers / percent rates
│   │   ├── accounting.py          # mark vs liquidation equity, NET P&L, fill math
│   │   ├── position_sizing.py     # full-long notional from cash + max size
│   │   ├── state_machine.py       # session state transitions
│   │   ├── recovery.py            # startup: RUNNING/STOPPING → STOPPED
│   │   ├── strategy/
│   │   │   ├── base.py            # Strategy protocol → Signal
│   │   │   └── dual_ema.py        # EMA(9)/EMA(21) crossover on closed bars
│   │   ├── control/
│   │   │   ├── controller.py      # Trading Controller
│   │   │   └── risk.py            # Risk Manager
│   │   ├── execution/
│   │   │   ├── port.py            # ExecutionEngine protocol
│   │   │   └── simulation.py      # SimulationExecutionEngine only (no real-money module in 003)
│   │   ├── pipeline.py            # orchestrate MD → strategy → control → risk → exec
│   │   ├── session_service.py     # create/start/stop/emergency + queries
│   │   └── worker.py              # RUNNING loop: poll closed candles via Clock
│   └── ...
└── tests/
    ├── unit/
    │   ├── test_accounting.py
    │   ├── test_dual_ema.py
    │   ├── test_position_sizing.py
    │   ├── test_state_machine.py
    │   ├── test_duplicate_candle.py
    │   ├── test_risk_rejects.py
    │   ├── test_max_trades.py
    │   ├── test_forced_close.py
    │   └── test_recovery.py
    ├── contract/
    │   └── test_simulation_api.py
    └── integration/
        └── test_simulation_pipeline.py

frontend/
├── vite.config.ts                 # proxy /simulation → backend
├── src/
│   ├── pages/
│   │   ├── AutoTradingPage.tsx    # simulation configure/monitor
│   │   └── PortfolioPage.tsx      # optional thin recent-session summary only
│   ├── features/
│   │   └── simulation/
│   │       ├── SessionConfigForm.tsx
│   │       ├── SessionStatusPanel.tsx
│   │       ├── EconomicsPanel.tsx
│   │       ├── DecisionJournal.tsx
│   │       ├── TradeJournal.tsx
│   │       ├── SimulationBadge.tsx
│   │       └── useSimulationSession.ts
│   ├── services/
│   │   └── simulationApi.ts
│   └── __tests__/
│       └── simulation*.test.tsx
```

**Structure Decision**: Keep dual-package layout. Add a dedicated
`backend/app/simulation/` package so strategy/control/risk/accounting never
import XT types. Feature 002 `market_data` remains the only exchange-facing
boundary for prices/candles. Frontend gains `features/simulation/` on Auto
Trading; Portfolio stays non-portfolio-product (optional summary only).

## Complexity Tracking

> No constitution violations requiring justification. SQLite is required by
> Constitution XV for domain persistence and matches the user’s planning
> decision for sessions/journals (unlike Feature 002 UI prefs).
