# Implementation Plan: Additional Strategies

**Branch**: `006-additional-strategies` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-additional-strategies/spec.md`  
(including Session 2026-08-12 clarifications)

## Summary

Register four conventional strategies — **RSI**, **MACD**, **Bollinger Bands**,
and **Breakout** — on the existing Feature 005 strategy framework. Each
implements the shared `Strategy` contract, registers with stable ids /
parameter schemas / defaults / constraints / `min_history_candles` (`S`), and
returns BUY/SELL/HOLD only. Simulation and Backtest resolve them through the
existing registry path with no strategy-specific engine branches. Dual EMA
behavior remains unchanged. Signal rules: RSI and Bollinger use **recovery
crossovers**; MACD uses line/signal crossover; Breakout emits on **every new
extreme** (trend-following). History contract reuses Dual EMA: reject
backtest if count &lt; `S`; HOLD until `S+1`.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: Existing FastAPI + SQLAlchemy + SQLite; Vite + React.
Reuse `app.strategy` registry, `ParamDef` / validation, `GET /strategies`,
`StrategyConfigFields`. No new HTTP resources beyond extended list payload.
No WebSockets. No XT trading APIs. No real-money mode.

**Storage**: No new tables or columns. Persist via existing
`strategy_id` + `strategy_params` on simulation sessions and backtest runs.

**Testing**: pytest unit (golden signal fixtures per strategy, param
validation, `S` / `S+1` warm-up, Dual EMA continuity regression); contract
(`GET /strategies` length 5 + schemas); integration (sim + backtest same
class path for at least one new id). Vitest: selector lists new strategies;
dynamic params render (including `decimal_string` for Bollinger `stdDev`).

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Evaluate remains O(n) over closed candles per tick;
registry list O(5). No new network hops.

**Constraints**:
- Strategies advisory only; never mutate balances/positions
- Same implementation for Simulation and Backtest
- Canonical ids: `rsi`, `macd`, `bollinger_bands`, `breakout`
- Dual EMA continuity tests must pass unmodified
- No optimization / ranking / ML / multi-strategy / sentiment / leverage /
  shorting / real money
- UI stays under Auto Trading; no hard-coded per-strategy field components

**Scale/Scope**: Five registered strategies total; single local operator

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No risk/bound changes; strategies advisory |
| II Simulation before real money | Pass | Sim + backtest only; FR-015 |
| III–IV Pipeline / controller–risk | Pass | Existing pipeline; strategies do not execute |
| V Explicit session boundaries | Pass | Selection at create; bounds unchanged |
| VI Net P&L | Pass | Unaffected |
| VII Decision traceability | Pass | Id + params already persisted |
| VIII Fail safe | Pass | Invalid params reject; warm-up HOLD; insufficient history |
| IX Emergency stop | Pass | Unchanged |
| X Intentional simplicity | Pass | Four thin strategy modules + optional shared indicators helper |
| XI Conventional strategies | Pass | RSI, MACD, Bollinger, Breakout — textbook defaults |
| XII Evidence, not guarantees | Pass | No profit claims |
| XIII Three primary UI areas | Pass | Auto Trading only |
| XIV Responsive UX | Pass | Existing `StrategyConfigFields` |
| XV Python / React / SQL | Pass | No schema migration |
| XVI–XVIII Adapter / credentials | Pass | No new XT APIs |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Golden fixtures + continuity |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Design adds registry entries and
indicator algorithms only; Controller/Risk/Execution unchanged; Dual EMA
untouched; fail-closed validation and Dual EMA `S`/`S+1` history contract
extended consistently to new strategies.

## Project Structure

### Documentation (this feature)

```text
specs/006-additional-strategies/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── additional-strategies-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── strategy/
│   │   ├── __init__.py              # Import dual_ema + four new modules
│   │   ├── indicators.py            # NEW optional shared EMA/SMA/RSI helpers
│   │   ├── rsi.py                   # NEW
│   │   ├── macd.py                  # NEW
│   │   ├── bollinger.py             # NEW
│   │   ├── breakout.py              # NEW
│   │   ├── dual_ema.py              # UNCHANGED behavior (may call shared EMA)
│   │   ├── base.py / registry.py / params.py / serialize.py  # reuse
│   ├── main.py                      # Ensure new modules import for registration
│   └── ...
└── tests/
    ├── unit/
    │   ├── test_rsi_strategy.py
    │   ├── test_macd_strategy.py
    │   ├── test_bollinger_strategy.py
    │   ├── test_breakout_strategy.py
    │   ├── test_dual_ema_continuity.py   # must still pass
    │   └── ...
    ├── contract/
    │   └── test_strategies_api.py        # expect 5 strategies
    └── integration/
        └── test_strategy_shared_sim_backtest.py  # extend for a new id

frontend/
├── src/
│   ├── services/strategiesApi.ts    # FALLBACK_STRATEGIES include all five
│   ├── features/strategy/StrategyConfigFields.tsx  # already dynamic
│   └── __tests__/strategyConfig.test.tsx
└── ...
```

**Structure Decision**: Extend existing `backend/app/strategy/` package and
dynamic frontend selector. No new API routers, DB migrations, or form
components beyond fallback catalog updates and tests.

## Complexity Tracking

> No constitution violations requiring justification.
