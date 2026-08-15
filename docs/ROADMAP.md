# CryptoAutoTrading Roadmap

## Purpose

CryptoAutoTrading is being developed incrementally from market observation and
safe historical/simulated trading toward composable Torque trading programs,
Grammatical Evolution, and eventually carefully controlled autonomous
real-money trading.
    
This roadmap defines:

- feature sequence;
- major dependencies;
- current status;
- architectural milestones;
- long-term development direction.

Detailed requirements belong under:

```text
specs/NNN-feature-name/
```

Project-wide engineering rules belong in:

```text
.specify/memory/constitution.md
```

Development procedure belongs in:

```text
core/DEVELOPMENT_WORKFLOW.md
```

---

# Status Definitions

Each feature has one status:

| Status | Meaning |
|---|---|
| PLANNED | Approved direction; implementation not started |
| IN PROGRESS | Specification and/or implementation is actively underway |
| BLOCKED | Cannot proceed because a dependency or decision is unresolved |
| DEFERRED | Intentionally postponed |
| DONE | Implementation, tests, validation/convergence, docs, and completion checks finished |

A feature MUST NOT be marked DONE merely because code was generated.

---

# Phase A — Application & Trading Foundations

## Goal

Build the minimum trustworthy trading platform:

```text
Application
    ↓
Market Data
    ↓
Simulation
    ↓
Backtesting
    ↓
Strategy Framework
    ↓
Conventional Strategies
    ↓
Strategy Comparison
```

| ID | Feature | Status |
|---|---|---|
| 001 | Application Foundation | DONE |
| 002 | Market Data | DONE |
| 003 | Simulation Trading Core | DONE |
| 004 | Backtesting Core | DONE |
| 005 | Strategy Framework | DONE |
| 006 | Additional Strategies | DONE |
| 007 | Strategy Comparison | DONE |

---

## 001 — Application Foundation

Established the application skeleton.

Key outcomes:

- FastAPI backend;
- React/Vite frontend;
- Dashboard;
- Auto Trading;
- Portfolio;
- responsive application shell;
- health contract;
- automated test foundation.

Status: `DONE`

---

## 002 — Market Data

Established normalized public market data.

Key outcomes:

- XT Spot public adapter;
- trading-pair discovery;
- quotes;
- candlesticks;
- normalized market-data models;
- stale-state handling;
- favorites/preferences;
- historical candle range support used by Backtest.

Status: `DONE`

---

## 003 — Simulation Trading Core

Established safe simulated trading.

Key outcomes:

- simulation sessions;
- Controller;
- Risk;
- simulated execution;
- accounting;
- capital boundaries;
- max trades;
- profit/loss boundaries;
- decision journal;
- emergency stop;
- no real exchange orders.

Status: `DONE`

---

## 004 — Backtesting Core

Established historical evaluation using the same trading authority.

Key outcomes:

- historical candle execution;
- HistoricalExecutionAdapter;
- next-open fills;
- end-of-run flatten;
- fees/slippage;
- decision/trade history;
- metrics;
- Buy & Hold baseline;
- deterministic backtests;
- persisted run history.

Status: `DONE`

---

## 005 — Strategy Framework

Made strategies pluggable.

Key outcomes:

- shared strategy registry;
- shared Strategy contract;
- canonical strategy ids;
- effective strategy parameters;
- strategy schema API;
- same strategy implementation for Simulation and Backtest;
- Dual EMA configurable through registry.

Status: `DONE`

---

## 006 — Additional Strategies

Expanded conventional deterministic strategy coverage.

Strategies:

- Dual EMA;
- RSI;
- MACD;
- Bollinger Bands;
- Breakout.

Key outcomes:

- registry-based implementation;
- parameter validation;
- strategy-specific warm-up;
- deterministic golden fixtures;
- dynamic frontend parameter rendering.

Status: `DONE`

---

## 007 — Strategy Comparison

### Goal

Compare multiple strategy configurations fairly over the same market data and
historical window.

Planned/implemented concepts include:

- 2–5 comparison legs;
- duplicate strategy ids allowed with different parameters;
- shared candle fetch;
- synchronous comparison;
- same starting conditions;
- same fees/slippage;
- individual underlying backtests;
- comparison-originated backtest marker;
- inspectable leg results;
- comparison metrics;
- both round-trip and fill counts;
- retained comparison history;
- 10 completed + 5 failed comparisons.

### Why it matters

Feature 007 creates the first systematic bridge between:

```text
single strategy evaluation
```

and later:

```text
automated strategy/program search
```

Status: `DONE`

---

# Phase B — Shared Trading Infrastructure

## Goal

Finish reusable trading infrastructure before Torque and real-money
automation.

This phase is deliberately before Torque.

Torque should reuse these components rather than inventing alternatives.

```text
Defaults
   ↓
Portfolio / Capital Allocation
   ↓
Risk
   ↓
Simulation History & Results
   ↓
Execution Abstraction
```

| ID | Feature | Status |
|---|---|---|
| 008 | Trading & Experiment Defaults | DONE |
| 009 | Portfolio & Capital Allocation Core | DONE |
| 010 | Advanced Risk Management | DONE |
| 011 | Simulation History & Results | IN PROGRESS |
| 012 | Execution Abstraction | PLANNED |

---

## 008 — Trading & Experiment Defaults

### Goal

Centralize reusable operator defaults currently repeated across forms and
future experiment configuration.

Possible defaults:

Trading:

- symbol;
- timeframe;
- starting capital;
- allocated capital;
- maximum position size;
- fee rate;
- slippage rate;
- max trades;
- profit target;
- maximum loss.

Backtesting:

- default historical window preferences;
- result/history display preferences.

Strategies:

- preferred strategy;
- optional preferred parameter defaults.

Experiments:

- default seed;
- future population size;
- generations;
- evaluation defaults.

### Core rule

Settings are defaults only.

At creation:

```text
Settings
   ↓ copy
Run / Session / Experiment Configuration
   ↓
Persisted Effective Configuration
```

Changing Settings MUST NOT rewrite historical configurations.

Status: `DONE`

---

## 009 — Portfolio & Capital Allocation Core

### Goal

Create the **Simulation Portfolio**: an exchange-style view of simulation
quote cash (USDT), holdings created by simulated execution, public
mark-to-market, P&L, and explicit **quote-cash reservation** for later
Risk/Torque — not a manual holdings book and not a live XT account.

Required for:

- operator inspection of simulation wealth (total value, available USDT,
  assets, weights, P&L);
- fill→accounting so BUY/SELL updates USDT and the traded asset;
- multiple concurrent programs via reservations;
- later Feature 013 Real XT Portfolio on the same domain (separate mode).

```text
Simulation Portfolio
├── holdings (USDT from funding; BTC/ETH/… from simulated fills)
├── total value / equity
├── available / reserved / deployed (capital; secondary UI)
├── allocations (compact)
└── positions (open simulated exposure, distinct from holdings)
```

Operator funds **simulation USDT only**. No UI to type BTC/ETH quantities.
Strategies never write balances. Pipeline: Strategy → Controller → Risk →
Execution → Portfolio/Accounting.

Feature 013 maps XT private balances later; Feature 009 must not call XT
private APIs and must not look like a live exchange account.

Status: `DONE`

---

## 010 — Advanced Risk Management

### Goal

Move beyond basic per-session constraints toward reusable portfolio-level risk
authority.

Potential areas:

- portfolio exposure;
- allocation limits;
- per-strategy exposure;
- per-symbol exposure;
- drawdown protection;
- daily/session loss limits;
- trade-frequency limits;
- concentration limits;
- global stop conditions;
- consistent risk rejection reasons.

Exact rules must be specified before implementation.

Status: `DONE`

---

## 011 — Simulation History & Results

### Goal

Make Simulation sessions behave like saved runs/logs: list, reopen, inspect,
freeze terminal economics when valuation is valid, and delete with confirmation
— without changing Feature 003 lifecycle semantics or Feature 010 Risk rules,
and without automatic resume after backend restart.

In scope:

- list persisted Simulation sessions;
- distinguish running, stopped, failed/interrupted states;
- open any historical Simulation;
- inspect effective configuration actually used;
- inspect symbol, timeframe, strategy and effective strategy parameters;
- inspect starting capital;
- inspect trades and decision journal (including Risk rejection reasons);
- inspect timestamps and stop/completion reason;
- persist/freeze final run economics at termination when a valid valuation is
  available (ending equity/value, P&L, return, fees/slippage and related
  metrics) so later market prices cannot rewrite historical results;
- delete historical simulations with explicit confirmation and safe rules for
  active/bound sessions;
- preserve that frontend navigation, remount, and browser refresh do not stop
  an active backend Simulation.

Out of scope:

- automatic resume after backend restart;
- crash recovery/reconciliation;
- rebuilding workers after process restart;
- automatic continuation of `unsafe_unflattened` sessions;
- multi-active Simulation support;
- Feature 010 Risk semantic changes.

Backend restart recovery/resume remains for Feature 014 — Live Paper-Trading
Hardening.

Status: `PLANNED`

---

## 012 — Execution Abstraction

### Goal

Formalize one execution interface across historical, simulated, and real
trading.

Target architecture:

```text
                 ┌─ HistoricalExecutionAdapter
Trading Intent → ├─ SimulationExecutionAdapter
                 └─ RealExecutionAdapter
```

Controller and Risk should not care which execution mode is active.

Feature 012 should consolidate existing historical/simulation semantics without
changing their established behavior.

Status: `PLANNED`

---

# Phase C — Exchange Integration & Controlled Real Trading

## Goal

Connect the mature trading pipeline to XT without immediately enabling
autonomous real-money trading.

| ID | Feature | Status |
|---|---|---|
| 013 | XT Account / Private API Integration | PLANNED |
| 014 | Live Paper-Trading Hardening | PLANNED |
| 015 | Real-Money Manual/Confirmed Execution | PLANNED |

---

## 013 — XT Account / Private API Integration

### Goal

Introduce authenticated account capabilities behind exchange adapters.

Potential scope:

- account authentication;
- account balances;
- available balances;
- open orders;
- order status;
- order placement adapter;
- order cancellation;
- normalized exchange errors;
- rate-limit handling;
- credential configuration.

### Safety

Private API integration does NOT mean autonomous trading.

No strategy should call XT directly.

Target:

```text
Strategy
   ↓
Controller
   ↓
Risk
   ↓
RealExecutionAdapter
   ↓
XT Private Adapter
```

Status: `PLANNED`

---

## 014 — Live Paper-Trading Hardening

### Goal

Prove the pipeline can operate safely for longer-running live market sessions
before depending on it for real money.

Areas should include:

- restart/recovery;
- state persistence;
- duplicate-event protection;
- stale market data;
- temporary network failure;
- exchange/API outages;
- reconciliation;
- execution retries where safe;
- deterministic order state;
- emergency stop;
- logging/observability;
- long-running simulation tests.

Status: `PLANNED`

---

## 015 — Real-Money Manual/Confirmed Execution

### Goal

Allow real orders only with explicit operator confirmation.

Example:

```text
Strategy → BUY
Controller → APPROVE
Risk → APPROVE
Execution → WAITING FOR CONFIRMATION

Operator confirms

RealExecutionAdapter → XT
```

Requirements should include:

- unmistakable REAL MONEY state;
- explicit enablement;
- confirmation;
- risk check immediately before execution;
- account reconciliation;
- audit history;
- exchange failure handling;
- emergency stop.

### Important

Feature 015 is NOT autonomous trading.

Status: `PLANNED`

---

# Phase D — Torque Trading Programs

## Goal

Build a compositional trading-program representation on top of the already
working trading infrastructure.

Torque is a program layer, not another trading engine.

| ID | Feature | Status |
|---|---|---|
| 016 | Torque Trading Program Core | PLANNED |
| 017 | Torque Capital Allocation | PLANNED |
| 018 | Torque Signal Composition | PLANNED |

---

## 016 — Torque Trading Program Core

### Goal

Represent trading behavior as composable Torque programs suitable for both
manual construction and later grammar generation.

Basic building blocks may include:

```text
Strategy invocation
Strategy parameters
Time windows
Sequential composition
```

Conceptual program:

```text
Sequence(
    RSI(
        period=14,
        oversold=30,
        overbought=70,
        start=T1,
        end=T2
    ),
    MACD(
        fastPeriod=12,
        slowPeriod=26,
        signalPeriod=9,
        start=T2,
        end=T3
    )
)
```

Meaning:

```text
T1 ───────── T2 ───────── T3
     RSI           MACD
```

Exact Torque syntax belongs in Feature 016.

### Architectural rule

```text
Torque Program
      ↓
Trading Intent
      ↓
Controller
      ↓
Risk
      ↓
Execution
```

Status: `PLANNED`

---

## 017 — Torque Capital Allocation

### Goal

Allow Torque programs to divide available capital between concurrent strategy
branches.

Example:

```text
Capital = €500

Allocate(
    0.50,
    RSI(...),

    0.50,
    MACD(...)
)
```

Conceptually:

```text
                  €500
                   │
             ┌─────┴─────┐
             │           │
           €250         €250
             │           │
            RSI         MACD
```

Both may operate during the same historical/live interval.

Feature 017 MUST reuse Feature 009 capital allocation.

Status: `PLANNED`

---

## 018 — Torque Signal Composition

### Goal

Allow strategies to cooperate on trading intent.

Possible constructs:

```text
AND
OR
Vote
WeightedVote
Confirm
Conditional
```

Conceptual example:

```text
Confirm(
    RSI(...),
    MACD(...)
)
```

or:

```text
Vote(
    RSI(...),
    MACD(...),
    BollingerBands(...)
)
```

The composition produces intent.

Controller and Risk remain authoritative.

Status: `PLANNED`

---

# Phase E — Grammatical Evolution

## Goal

Use Grammatical Evolution to search the space of valid Torque trading
programs.

| ID | Feature | Status |
|---|---|---|
| 019 | Grammatical Evolution Search | PLANNED |
| 020 | Evolution Experiments & Results | PLANNED |
| 021 | Train / Validation / Test | PLANNED |
| 022 | Advanced Fitness | PLANNED |
| 023 | Regime-Aware Programs | PLANNED |

---

## 019 — Grammatical Evolution Search

### Goal

Map GE genotypes through a grammar into executable Torque trading programs.

Architecture:

```text
Genotype
   ↓
Grammar
   ↓
Torque Phenotype
   ↓
Torque Evaluator
   ↓
Backtest
   ↓
Metrics
   ↓
Fitness
```

The grammar may eventually search:

- strategy type;
- strategy parameters;
- strategy order;
- time windows;
- capital allocation;
- signal composition.

### Initial fitness

Initial formulation:

```text
Fitness =
    TorqueProgramNetProfit
    - BuyAndHoldNetProfit
```

where both use comparable:

- capital;
- symbol;
- historical period;
- market data;
- fee assumptions;
- slippage assumptions.

Higher fitness is better.

Exact fitness and GE mechanics must be specified in Feature 019.

Status: `PLANNED`

---

## 020 — Evolution Experiments & Results

### Goal

Make GE experimentation reproducible and inspectable.

Persist or reproducibly identify:

- experiment id;
- grammar;
- genotype;
- phenotype;
- effective Torque program;
- random seed;
- population size;
- generations;
- operators;
- market data;
- train period;
- fitness;
- metrics;
- generation statistics;
- best individuals;
- runtime.

Potential UI:

```text
Experiments
├── configuration
├── progress/results
├── generations
├── best programs
└── program inspection
```

Status: `PLANNED`

---

## 021 — Train / Validation / Test

### Goal

Prevent optimization leakage and provide scientifically meaningful evaluation.

Data roles:

```text
Historical Data
      │
      ├── TRAIN
      │     └── GE search
      │
      ├── VALIDATION
      │     └── selection / robustness
      │
      └── TEST
            └── final unseen evaluation
```

Test performance MUST NOT influence evolution.

Status: `PLANNED`

---

## 022 — Advanced Fitness

### Goal

Improve beyond simple excess-profit optimization.

Potential objective components:

```text
Net return
Excess return vs Buy & Hold
Max drawdown
Downside risk
Trade count
Turnover
Fees/slippage
Stability
Robustness across windows
```

Example future form:

```text
fitness =
    excess_return
    - λ1 × max_drawdown
    - λ2 × trading_cost
    - λ3 × instability
```

Multi-objective optimization may also be evaluated.

Do not select a complicated fitness function without empirical justification.

Status: `PLANNED`

---

## 023 — Regime-Aware Programs

### Goal

Allow programs to adapt behavior based on explicit market conditions.

Potential regime information:

- trend;
- volatility;
- volume;
- liquidity;
- market structure;
- future sentiment/news signals.

Conceptual Torque behavior:

```text
IF high_volatility:
    use Strategy A
ELSE:
    use Strategy B
```

or GE may evolve such structures.

Regime information remains input to trading logic, never execution authority.

Status: `PLANNED`

---

# Phase F — Autonomous Real-Money Trading

| ID | Feature | Status |
|---|---|---|
| 024 | Autonomous Real-Money Trading | PLANNED |

---

## 024 — Autonomous Real-Money Trading

### Goal

Allow validated strategies/Torque programs to operate without confirmation for
each individual order.

This is the highest-risk milestone in the roadmap.

It MUST NOT be enabled simply because earlier features exist.

### Required safety foundation

Before implementation approval, review at minimum:

```text
Portfolio authority
Capital allocation
Advanced Risk
Execution abstraction
XT private API
Account reconciliation
Paper-trading evidence
Real-order execution evidence
Emergency stop
Restart/recovery
Decision journal
Failure handling
Configuration persistence
Torque determinism
GE evaluation methodology
Train/Validation/Test separation
```

### Activation model

Autonomous real-money trading must be explicitly enabled.

Default:

```text
AUTONOMOUS REAL MONEY = OFF
```

A backtest, comparison, experiment, or GE result MUST NOT automatically enable
it.

Status: `PLANNED`

---

# Future Candidates — Not Yet Numbered

These are intentionally NOT committed roadmap features yet.

They should receive feature numbers only when there is sufficient evidence and
priority.

Potential areas:

- market sentiment;
- news ingestion;
- social sentiment;
- market regime detection;
- multi-symbol Torque programs;
- portfolio-level GE;
- walk-forward optimization;
- Monte Carlo robustness;
- paper-vs-backtest drift analysis;
- execution quality analysis;
- parameter sensitivity;
- experiment comparison;
- strategy/program versioning;
- notification/alert system;
- advanced reporting;
- model-based strategies;
- ML strategies.

Do not implement these merely because they are listed here.

---

# Major Architectural Dependency Map

```text
001 Application Foundation
        │
        ▼
002 Market Data
        │
        ▼
003 Simulation Trading Core
        │
        ▼
004 Backtesting Core
        │
        ▼
005 Strategy Framework
        │
        ▼
006 Additional Strategies
        │
        ▼
007 Strategy Comparison
        │
        ▼
008 Trading & Experiment Defaults
        │
        ▼
009 Portfolio & Capital Allocation
        │
        ▼
010 Advanced Risk Management
        │
        ▼
011 Simulation History & Results
        │
        ▼
012 Execution Abstraction
        │
        ├──────────────────────┐
        ▼                      │
013 XT Private Integration     │
        │                      │
        ▼                      │
014 Paper-Trading Hardening    │
        │                      │
        ▼                      │
015 Confirmed Real Execution   │
        │                      │
        └──────────┬───────────┘
                   ▼
          016 Torque Program Core
                   │
                   ▼
          017 Torque Capital Allocation
                   │
                   ▼
          018 Torque Signal Composition
                   │
                   ▼
          019 GE Search
                   │
                   ▼
          020 Experiment Management
                   │
                   ▼
          021 Train / Validation / Test
                   │
                   ▼
          022 Advanced Fitness
                   │
                   ▼
          023 Regime-Aware Programs
                   │
                   ▼
          024 Autonomous Real Trading
```

This diagram describes the preferred development path.

Not every feature is technically dependent on every feature immediately above
it.

---

# Reuse Architecture

The project should progressively converge on these shared authorities:

```text
                  Market Data
                      │
          ┌───────────┼───────────┐
          │           │           │
      Strategy      Torque       Future
          │           │
          └─────┬─────┘
                ▼
            Controller
                │
                ▼
               Risk
                │
                ▼
             Execution
       ┌────────┼────────┐
       │        │        │
 Historical Simulation  Real
       │        │        │
       └────────┼────────┘
                ▼
       Portfolio / Accounting
                │
                ▼
        Journal / Metrics
```

GE sits above Torque:

```text
GE
 ↓
Torque Program
 ↓
existing trading architecture
```

It does not receive its own Controller, Risk, Execution, or Accounting engine.

---

# Safety Gates

## Gate A — Before Real Orders

Before Feature 015:

- execution abstraction must work;
- private XT integration must work;
- Risk must remain authoritative;
- capital must be explicit;
- emergency stop must be tested.

---

## Gate B — Before GE

Before Feature 019:

- Torque programs must execute deterministically;
- Torque must reuse Backtest;
- capital allocation must be explicit;
- strategy composition semantics must be specified;
- evaluation configuration must be persistable.

---

## Gate C — Before Autonomous Real Money

Before Feature 024:

- real execution must already work with confirmation;
- paper trading must be hardened;
- account reconciliation must exist;
- emergency stop must work;
- Risk must be tested;
- failure recovery must be tested;
- Torque/strategy execution must be deterministic;
- GE results must be evaluated out of sample where applicable.

---

# Roadmap Maintenance Rules

When a feature specification is created:

1. confirm the feature exists here;
2. review its dependencies;
3. update description if clarification materially changes scope.

When implementation begins:

```text
PLANNED → IN PROGRESS
```

When a blocking dependency is discovered:

```text
IN PROGRESS → BLOCKED
```

When intentionally postponed:

```text
PLANNED/IN PROGRESS → DEFERRED
```

Before marking DONE:

1. implementation complete;
2. required tests green;
3. analysis findings resolved;
4. quickstart/smoke complete;
5. convergence complete;
6. documentation current;
7. downstream roadmap impact reviewed.

Then:

```text
IN PROGRESS → DONE
```

Do not change unrelated feature statuses during routine roadmap maintenance.

---

# Current Position

Current completed foundation:

```text
001 → DONE
002 → DONE
003 → DONE
004 → DONE
005 → DONE
006 → DONE
007 → DONE
008 → DONE
009 → DONE
010 → DONE
```

Current active milestone:

```text
011 → Simulation History & Results
```

Next planned milestone:

```text
012 → Execution Abstraction
```

The near-term objective is therefore:

```text
simulation history & frozen results
        ↓
abstract execution
        ↓
connect controlled real trading
        ↓
build Torque on mature reusable infrastructure
```

---

# Guiding Principle

CryptoAutoTrading should not evolve by adding increasingly powerful independent
components.

It should evolve by making one trading architecture progressively more capable:

```text
Observe
  ↓
Simulate
  ↓
Backtest
  ↓
Compare
  ↓
Control Capital
  ↓
Control Risk
  ↓
Abstract Execution
  ↓
Trade with Confirmation
  ↓
Compose with Torque
  ↓
Search with GE
  ↓
Validate Out-of-Sample
  ↓
Automate Carefully
```