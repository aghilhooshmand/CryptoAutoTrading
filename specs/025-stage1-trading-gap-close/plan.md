# Implementation Plan: Stage-1 Trading Gap-Close

**Branch**: `025-stage1-trading-gap-close` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 025 — bounded Stage-1 gap-close before Feature 015:
per-position fixed TP/SL (% config; derived absolute levels; high→TP / low→SL;
no entry-bar eval; no mid-position edits; mode-native exit fills); OHLC strategy
candle enrichment; Stochastic + Keltner/ATR + ROC/Momentum (+ volume only if
gate passes — **deferred**); document intentional Sim vs Backtest fill
differences; minimal UI; tests + MVP-1 validation gate. No Real, Torque, GE,
014 expansion, Portfolio redesign, ticks.

## Summary

Add optional per-position take-profit / stop-loss to the **existing** Simulation
and Backtest pipelines without a second engine. TP/SL **triggers** from closed
candle high/low after the entry bar; **fills** still use Simulation live mark /
Backtest next-open. Enrich strategy candle input to **OHLC** and register three
new close/range primitives. Keep Controller/Risk/Execution authority; minimal
operator UI for percentages and live absolute levels / exit reasons.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript/React (frontend)

**Primary Dependencies**: Existing FastAPI Simulation + Backtest; Strategy
registry (005/006); Feature 012 Simulation / Historical execution adapters;
SQLAlchemy/SQLite; public market_data `Candlestick` (already OHLC)

**Storage**: Extend `SimulationSessionRow`, Backtest run config persistence,
and optional `OperatorDefaultsRow` with TP/SL **percent** fields; persist
derived absolute TP/SL prices (+ entry candle cursor) on session/engine state
while long

**Testing**: pytest unit (TP/SL triggers, precedence, entry-bar skip, accounting
cycles, new strategies) + Backtest engine fixtures + Simulation pipeline
fixtures + contract create/status fields + frontend form/status ~375px smoke

**Target Platform**: Local operator machines (same as Features 003–014)

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: No change to ~2s Simulation worker class; Backtest remains
single-pass over series

**Constraints**: Spec FR-001–FR-019 + Clarifications Q1–Q6; constitution I, III,
IV, V, VI, VII, VIII, X, XI, XII, XXXII; no RealExecutionAdapter; no ticks;
volume strategy deferred (R6)

**Scale/Scope**: One protective-exit path shared conceptually by Sim/Backtest;
OHLC candle type extension; three new strategies; thin UI/API field additions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | SL before TP; session stops first; fail closed; no invented fills |
| II Simulation before real | Pass | Paper/historical only; 015 untouched |
| III Single pipeline | Pass | Hooks in existing pipeline/engine; no second engine |
| IV Controller / Risk | Pass | Protective exit intent still through Controller→Risk→Execution |
| V Explicit boundaries | Pass | Session stops remain; TP/SL additive |
| VI Net P&L | Pass | Fees/slippage on fills only; trigger levels exclude fees |
| VII Traceability | Pass | Distinct exit reasons; journals/history |
| VIII Fail safe | Pass | No invent; unsafe mark fail closed |
| IX Emergency stop | Pass | Unchanged; still precedes TP/SL |
| X Intentional simplicity | Pass | % only; no mid-position edits; no ticks |
| XI Conventional strategies | Pass | Registry additions; shared Sim/Backtest |
| XII Evidence | Pass | FR-018 / quickstart / MVP-1 gate |
| XIII–XIV UI | Pass | Minimal fields; ~375px; no Portfolio redesign |
| XV Stack | Pass | Existing Python + React |
| XXXII Execution | Pass | Mode-native fills; Real stays unavailable |
| XXXIV Portfolio | Pass | Fill→Portfolio unchanged; no allocation expansion |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design reuses Simulation pipeline, Backtest engine, Strategy registry,
and Execution adapters. TP/SL is trigger logic + protective SELL intent, not a
bypass. OHLC enrichment is a minimal candle contract extension. Volume strategy
deferred. See [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/).

## Project Structure

### Documentation (this feature)

```text
specs/025-stage1-trading-gap-close/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── protective-exits.md
│   ├── strategy-ohlc-and-additions.md
│   └── sim-vs-backtest-semantics.md
├── spec.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks — not created by this command
```

### Source Code (repository root)

```text
backend/app/strategy/
├── base.py                  # CandleClose → OHLC (compat: existing strategies use close)
├── stochastic.py            # NEW
├── keltner.py               # NEW (ATR channel)
├── momentum_roc.py          # NEW
├── indicators.py            # ATR / stochastic helpers as needed
└── __init__.py              # register new strategies

backend/app/simulation/
├── pipeline.py              # OHLC lookback; TP/SL before strategy; entry-bar skip
├── session_service.py       # create/validate %; derive/clear absolute levels; session_to_dict
└── control/                 # protective intent path if thin helper needed (prefer reuse)

backend/app/backtest/
├── engine.py                # TP/SL before strategy; next-open protective fills
└── service.py               # config fields for TP/SL %

backend/app/db/
├── models.py                # session + defaults (+ backtest) TP/SL columns
└── session.py               # _ensure_column for SQLite

backend/app/api/
├── simulation.py            # create/status payload fields
└── (backtest / settings as already structured)

frontend/src/
├── services/simulationApi.ts
├── features/simulation/SessionConfigForm.tsx
├── features/simulation/SessionStatusPanel.tsx
├── features/backtest/BacktestConfigForm.tsx
└── features/settings/SettingsPanel.tsx   # optional default % only

backend/tests/unit|integration|contract/
frontend/src/__tests__/
docs/                        # short Sim vs Backtest semantics note if README pointer needed
```

**Structure Decision**: Extend existing Simulation, Backtest, and Strategy
packages only. No new trading engine, no private XT, no Portfolio redesign.

## Complexity Tracking

> No constitution violations requiring justification.
