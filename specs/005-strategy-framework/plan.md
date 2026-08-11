# Implementation Plan: Strategy Framework and Selection

**Branch**: `005-strategy-framework` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-strategy-framework/spec.md`  
(including Session 2026-08-11 clarifications)

## Summary

Make strategies **pluggable and selectable** while preserving
Market Data → Strategy → Controller → Risk → Execution. Introduce a shared
**strategy registry** and contract used by both Simulation (003) and Backtest
(004). Register **Dual EMA** as canonical id `dual_ema` (legacy alias
`dual_ema_9_21`) with editable periods defaulting to **9/21**. Persist
canonical id + effective parameters on sessions/runs; reject omitted/unknown
ids; scale Dual EMA warm-up (`S+1`) and backtest insufficient-history (`< S`)
with configured slow period. No real-money changes; no additional strategies
in this feature.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + SQLAlchemy 2.x + SQLite (existing); Vite +
React Router (existing). Extend Feature 003/004 create/list/detail paths.
Shared strategy package imported by `simulation/` and `backtest/` — no Dual EMA
fork. No WebSockets. No XT private SDKs.

**Storage**: Existing SQLite simulation/backtest DB. Add/extend columns:
`strategy_id` (canonical string) + `strategy_params` (JSON text of effective
parameters). Soft-read legacy `dual_ema_9_21` rows.

**Testing**: pytest (unit: registry resolve/alias/defaults/validation,
Dual EMA param continuity vs pre-migration 9/21, warm-up `S+1`, insufficient
`< S`; contract: `GET /strategies`, create sim/backtest require strategyId,
alias → persist `dual_ema`; integration: same Dual EMA instance path for
sim + backtest). Vitest + RTL for strategy selector + period fields on Auto
Trading Simulation and Backtest forms.

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Registry list and resolve are O(registered strategies)
local; no new network. Strategy evaluate cost unchanged vs Dual EMA today.

**Constraints**:
- Strategies return BUY/SELL/HOLD only; never mutate balances/positions
- Same registered implementation for Simulation and Backtest
- `strategyId` **required** on create (omit → reject; UI may pre-fill)
- Canonical id `dual_ema`; alias `dual_ema_9_21` → Dual EMA; new persists
  `dual_ema` + effective params
- Dual EMA defaults fast=9, slow=21; validate positive ints and fast < slow
- Warm-up HOLD until `S+1` closed candles; backtest fail if count `< S`
- Behavioral continuity for default 9/21 vs pre-migration Dual EMA
- No mid-session/mid-run strategy swap; no fourth primary nav; no real money
- No optimization / ML / multi-strategy / sentiment

**Scale/Scope**: Single local operator; one registered strategy (Dual EMA) in
v1; framework ready for later registrations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No weakening of risk/capital nesting; strategy remains advisory |
| II Simulation before real money | Pass | Framework for sim + backtest only; FR-014 no real money |
| III–IV Pipeline / controller–risk | Pass | Explicit goal: preserve Controller → Risk → Execution |
| V Explicit session boundaries | Pass | Strategy selection is config at create; session/backtest bounds unchanged |
| VI Net P&L | Pass | Unaffected (fees/slippage remain outside strategy) |
| VII Decision traceability | Pass | Strategy id/params persisted; journals remain |
| VIII Fail safe | Pass | Unknown/omit id and invalid params reject; warm-up HOLD |
| IX Emergency stop | Pass | Feature 003 emergency stop unchanged |
| X Intentional simplicity | Pass | One strategy registered; thin registry |
| XI Conventional strategies | Pass | Dual EMA only |
| XII Evidence, not guarantees | Pass | No profit claims |
| XIII Three primary UI areas | Pass | Under Auto Trading tabs |
| XIV Responsive UX | Pass | Selector + period fields at ~375px |
| XV Python / React / SQL | Pass | SQLite JSON params |
| XVI–XVIII Adapter / credentials | Pass | No new XT trading APIs |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Continuity + contract tests planned |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Shared `app/strategy` registry;
simulation and backtest resolve the same Dual EMA; Controller/Risk authority
unchanged; create fails closed on omit/unknown/invalid; UI under Auto Trading
only.

## Project Structure

### Documentation (this feature)

```text
specs/005-strategy-framework/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── strategy-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── strategy/                    # NEW shared strategy domain
│   │   ├── __init__.py
│   │   ├── base.py                  # Strategy protocol, CandleClose, StrategySignal
│   │   ├── registry.py              # register, resolve (alias), list, validate_params
│   │   ├── params.py                # ParamDef / validate helpers
│   │   └── dual_ema.py              # Dual EMA (moved/adapted from simulation.strategy)
│   ├── api/
│   │   ├── strategies.py            # GET /strategies
│   │   ├── simulation.py            # require strategyId + strategyParams
│   │   └── backtest.py              # require strategyId + strategyParams; min history via S
│   ├── simulation/
│   │   ├── pipeline.py              # resolve strategy from session params
│   │   ├── session_service.py       # resolve/persist canonical id + params
│   │   └── strategy/                # thin re-exports or remove after migrate
│   ├── backtest/
│   │   ├── engine.py                # resolve strategy; warm-up via instance
│   │   ├── limits.py                # insufficient_history uses strategy min (S)
│   │   └── service.py               # validate strategy on create
│   ├── db/models.py                 # strategy_params JSON; defaults dual_ema
│   └── main.py                      # mount /strategies
└── tests/
    ├── unit/
    │   ├── test_strategy_registry.py
    │   ├── test_dual_ema_params.py
    │   └── test_dual_ema_continuity.py
    ├── contract/
    │   ├── test_strategies_api.py
    │   └── (extend) test_simulation_api.py / test_backtest_api.py
    └── integration/
        └── test_strategy_shared_sim_backtest.py

frontend/
├── src/
│   ├── services/strategiesApi.ts    # list strategies
│   ├── features/strategy/
│   │   └── StrategyConfigFields.tsx # selector + dynamic param inputs
│   ├── features/simulation/SessionConfigForm.tsx
│   ├── features/backtest/BacktestConfigForm.tsx
│   └── __tests__/
│       └── strategyConfig.test.tsx
```

**Structure Decision**: Add shared `backend/app/strategy/` used by both
simulation and backtest. Migrate Dual EMA out of a simulation-only path.
Frontend adds reusable strategy config fields under Auto Trading forms.
Extend create contracts; add `GET /strategies` for UI schema.

## Complexity Tracking

> No constitution violations requiring justification.
