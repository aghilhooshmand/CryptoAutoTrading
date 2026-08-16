# CryptoAutoTrading Roadmap

## Purpose

CryptoAutoTrading is being developed incrementally from market observation and
safe historical/simulated trading toward controlled real XT trading, then
composable Torque trading programs, Grammatical Evolution, and eventually
carefully controlled autonomous real-money trading (destination only).

Post-Feature-014 audit (2026-08-16): next delivery is **025 Stage-1 Trading
Gap-Close**, then MVP-1 validation, then **015 Controlled Real**, then Torque
composition (016), then minimal GE — while freezing expansion of completed
infrastructure features unless a concrete defect requires it.
    
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
| 007 | Strategy Comparison | DONE (**FREEZE** polish) |

### Freeze guidance (post-audit 2026-08-16)

Feature 007 is sufficient for Stage-1. Do not expand comparison UX/analytics
unless a concrete defect blocks operation.

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
| 008 | Trading & Experiment Defaults | DONE (**FREEZE** expansion) |
| 009 | Portfolio & Capital Allocation Core | DONE (**FREEZE** allocation/reservation expansion; no UX redesign phase before 015) |
| 010 | Advanced Risk Management | DONE (**FREEZE** weight/advanced portfolio-risk expansion; keep session + portfolio max-loss as-is) |
| 011 | Simulation History & Results | DONE |
| 012 | Execution Abstraction | DONE |

### Infrastructure freeze (post-audit 2026-08-16)

The following are sufficient for the current milestones. Do **not** expand
them unless testing identifies a concrete defect or Feature 015 creates a
genuine requirement:

- Feature **007** Strategy Comparison (polish frozen);
- Feature **008** Settings / defaults expansion;
- Feature **009** allocation / reservation machinery (keep working; operator
  focus remains cash + holdings + position + P&L + allocated capital — no
  separate Portfolio redesign before 015);
- Feature **010** advanced Portfolio risk / per-symbol weight machinery;
- Feature **014** restart / recovery (see Phase C).

Working, tested, harmless architecture should be **preserved and frozen**.
Do not reopen completed specs merely to reduce theoretical complexity.

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

Status: `DONE`

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

Status: `DONE`

---

# Phase C — Exchange Integration & Controlled Real Trading

## Goal

Connect the mature trading pipeline to XT without immediately enabling
autonomous real-money trading.

**Execution order in this phase (IDs are stable; do not renumber):**

```text
013 DONE → 014 DONE → 025 Stage-1 Gap-Close → MVP-1 validation gate
        → 015 Controlled Real → MVP-2
```

Feature **025** uses the next free numeric ID so Features **015–024** keep
their established identifiers. Chronological delivery still places **025
before 015**.

| ID | Feature | Status |
|---|---|---|
| 013 | XT Account / Private API Integration | DONE |
| 014 | Live Paper-Trading Hardening | DONE (**FREEZE** — expand only for concrete defects) |
| 025 | Stage-1 Trading Gap-Close | PLANNED (**next**) |
| 015 | Real-Money Manual/Confirmed Execution | PLANNED (after 025 + MVP-1 validation) |

---

## 013 — XT Account / Private API Integration

### Goal

Introduce authenticated **read-only** account capabilities behind a private XT
adapter (balances, open orders, order status), with fail-closed credentials and
normalized private errors—without enabling live trading.

### MVP scope (Feature 013)

- account authentication (signed private client);
- account balances / available + locked;
- open orders;
- order status lookup;
- normalized exchange errors (incl. `timestamp_invalid`, `rate_limited`);
- bounded rate-limit handling on safe GETs;
- credential configuration (env/secrets, fail closed);
- minimal read-only inspect UI separate from Simulation Portfolio.

### Explicitly deferred (not Feature 013)

- order placement adapter;
- order cancellation;
- RealExecutionAdapter live fills;
- operator Real trading mode / confirmed execution (Feature 015);
- crash/restart hardening (Feature 014).

### Safety

Private API integration does NOT mean autonomous trading.

No strategy should call XT directly.

Target (future trading path; RealExecutionAdapter stays unavailable in 013):

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

Status: `DONE`

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

### Freeze guidance (post-audit 2026-08-16)

Feature 014 is **DONE and FROZEN**. Do not add further recovery architecture,
reconcile gates, or operational hardening unless testing exposes a concrete
correctness/safety defect or Feature 015 creates a genuine new requirement.
Do not reopen the completed 014 spec merely to reduce theoretical complexity.

Status: `DONE`

---

## 025 — Stage-1 Trading Gap-Close

### Goal

Close the remaining **concrete** Stage-1 gaps before Controlled Real trading
(Feature 015). This is a bounded product/safety gap-close — **not** a new
infrastructure phase.

**Proposed Spec-Kit identity (do not create until roadmap approved):**

- Feature ID: `025`
- Name: Stage-1 Trading Gap-Close
- Spec/branch slug: `025-stage1-trading-gap-close`

### In scope

- basic per-position **fixed** take-profit and stop-loss (percentage or
  price-based);
- TP/SL supported consistently enough in **Simulation and Backtest**;
- **closed-candle** TP/SL semantics are acceptable for this MVP and must be
  **explicit** in spec/docs/UI copy;
- TP/SL levels visible in the relevant operator UI;
- tests for TP, SL, strategy exit, and their interaction/precedence;
- verify and **document intentional** Simulation vs Backtest execution/fill
  differences; fix only **accidental** semantic inconsistencies;
- add a **bounded** set of approximately **3–4** additional conventional
  strategy/signal primitives for later Torque/GE diversity (conceptual
  diversity: e.g. momentum ≠ RSI, volatility channel ≠ Bollinger, optional
  volume only if XT candle volume is confirmed reliable for both Backtest and
  Simulation — **do not lock a volume strategy until that check passes**).

### Explicitly out of scope

- trailing stops; multi-level TP; dynamic/advanced stop systems;
- tick / intrabar / WebSocket infrastructure;
- additional recovery work (014 freeze);
- Portfolio redesign (009 remains implemented; freeze allocation expansion);
- advanced analytics; dozens of indicators; plugin architecture.

### MVP-1 validation gate (not a separate feature)

After Feature 025 implementation, run an explicit end-to-end acceptance /
convergence exercise:

```text
Backtest → select configuration → Simulation → BUY → position
→ TP / SL / strategy EXIT → accounting/P&L → history/results
→ safe stop / restart behavior (014 as-is)
```

Create additional implementation work **only** if this validation exposes
concrete defects. Do not turn the gate into another large feature.

Status: `PLANNED`

---

## 015 — Real-Money Manual/Confirmed Execution

### Goal

First **Controlled Real** trading milestone on XT: tiny, operator-supervised
sessions with confirmed exposure-increasing entries. Feature 015 is **NOT**
autonomous trading.

### Preconditions

- Feature 025 DONE;
- MVP-1 validation gate passed (or only residual defects scheduled);
- Features 012–014 available as frozen/supporting infrastructure;
- Feature 013 read path used to verify XT account/order state.

### Controlled Real MVP (MVP-2)

- one trading pair per Real session initially;
- one open position for that session;
- tiny configurable capital;
- short / local operator-supervised sessions initially;
- **exposure-increasing entry** requires explicit operator confirmation;
- **TP/SL exits** may execute automatically;
- **strategy exits** that reduce/close exposure may execute automatically;
- **emergency / STOP flatten** must not wait for confirmation when a safe
  execution is possible;
- Controller and Risk remain authoritative immediately before Real execution;
- XT order/account state must be **reconciled** rather than assuming success;
- Real mode must be **unmistakable** in the UI (targeted UI changes allowed;
  do not redesign Portfolio as a separate project).

### Architecture note

Prefer a path that can later move from confirmed entries → automatic entries
within hard risk limits **without** a second execution pipeline. Do **not**
implement autonomous Real entries in Feature 015.

Example (entries):

```text
Strategy → BUY
Controller → APPROVE
Risk → APPROVE
Execution → WAITING FOR CONFIRMATION
Operator confirms
RealExecutionAdapter → XT
```

Status: `PLANNED`

---

# Phase D — Torque Trading Programs

## Goal

Build a compositional trading-program representation on top of the already
working trading infrastructure.

Torque is a program layer, not another trading engine.

**Start Torque only after Feature 015 / MVP-2** (tiny controlled Real lifecycle
proven). Do not let Torque/GE delay the primary path to Controlled Real.

| ID | Feature | Status |
|---|---|---|
| 016 | Torque Trading Program Core | PLANNED (minimum useful Torque MVP; **absorbs** min. composition from 018) |
| 017 | Torque Capital Allocation | PLANNED (**DEFER** heavily — Risk/Portfolio own capital in Torque v1) |
| 018 | Torque Signal Composition | PLANNED (**MERGE direction into 016**; keep ID; do not implement as a separate near-term feature) |

---

## 016 — Torque Trading Program Core

### Goal

Minimum useful Torque MVP after Controlled Real (015): compose existing
strategy/signal primitives into programs that feed the **same** trading
pipeline.

### Torque MVP must support

- invoking existing strategy/signal primitives;
- parameters;
- **simple composition** such as AND / OR / vote (minimum useful portion of
  Feature 018 absorbed here);
- producing decisions through Controller → Risk → Execution → Portfolio;
- deterministic Backtest evaluation;
- one initial fitness interface for later GE.

### Torque MVP must NOT

- own execution or bypass Controller/Risk;
- require Torque-owned capital allocation (Feature 017 deferred);
- redesign the trading engine.

Basic building blocks may also include sequence/time windows where useful,
but **signal composition is required** for the first useful Torque (combining
strategies is the point).

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

### Goal (deferred)

Allow Torque programs to divide available capital between concurrent strategy
branches.

### Direction (post-audit 2026-08-16)

**DEFER heavily.** For the first Torque version, existing **Risk / Portfolio**
remain responsible for capital. Do not block Torque MVP or GE on Feature 017.
Keep this feature ID for a later capital-in-Torque capability; do not delete
or renumber yet.

Feature 017 MUST reuse Feature 009 capital allocation if/when implemented.

Status: `PLANNED` (deferred direction)

---

## 018 — Torque Signal Composition

### Goal

Allow strategies to cooperate on trading intent (AND / OR / Vote / Confirm /
Conditional, etc.).

### Direction (post-audit 2026-08-16)

**MERGE direction into Feature 016.** The minimum useful composition language
is part of Torque MVP, not a separate near-term delivery after a
sequence-only Torque. Keep Feature 018 ID for traceability; do not implement
018 as an independent phase before/alongside 016. Richer composition beyond
016 MVP may later reference this ID.

Controller and Risk remain authoritative.

Status: `PLANNED` (merge direction into 016)

---

# Phase E — Grammatical Evolution

## Goal

Use Grammatical Evolution to search the space of valid Torque trading
programs.

**Start after minimum Torque (016).** Feature 024 Autonomous Real remains a
destination only — not a near-term driver.

| ID | Feature | Status |
|---|---|---|
| 019 | Grammatical Evolution Search | PLANNED (after 016) |
| 020 | Evolution Experiments & Results | PLANNED (**DEFER** rich UI/persistence) |
| 021 | Train / Validation / Test | PLANNED (**minimum accompanies first GE** — simple chronological) |
| 022 | Advanced Fitness | PLANNED (**DEFER**) |
| 023 | Regime-Aware Programs | PLANNED (**DEFER**) |

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
- signal composition;
- (later) capital allocation — not required for first GE.

### First GE milestone (with Feature 019)

Requires:

- small grammar producing valid Torque programs;
- deterministic Backtest evaluation;
- simple fitness;
- population;
- selection / crossover / mutation;
- reproducible seed / config;
- **simple chronological train / validation / test** protection (minimum
  necessary portion of Feature 021 accompanies this work — not an elaborate
  ML/walk-forward framework yet).

Defer rich experiment UI/persistence (020), advanced multi-objective fitness
(022), and regime-aware evolution (023).

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

### Direction (post-audit 2026-08-16)

**DEFER** rich experiment UI and heavy persistence. First GE may use minimal
reproducibility (seed/config/results) without a full Experiments product UI.

Status: `PLANNED` (deferred richness)

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

### Direction (post-audit 2026-08-16)

The **minimum** chronological train/validation/test split is scientifically
necessary for first useful GE and should **accompany Feature 019**. Keep this
feature ID; do not build elaborate walk-forward optimisation yet.

Status: `PLANNED` (minimum with first GE)

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

### Direction (post-audit 2026-08-16)

**DEFER.** First GE uses simple fitness from Feature 019.

Status: `PLANNED` (deferred)

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

### Direction (post-audit 2026-08-16)

**DEFER.** Not part of near-term Torque/GE MVP.

Status: `PLANNED` (deferred)

---

# Phase F — Autonomous Real-Money Trading

| ID | Feature | Status |
|---|---|---|
| 024 | Autonomous Real-Money Trading | PLANNED (**destination only** — out of near-term scope) |

---

## 024 — Autonomous Real-Money Trading

### Goal

Allow validated strategies/Torque programs to operate without confirmation for
each individual order.

This is the highest-risk milestone in the roadmap.

It MUST NOT be enabled simply because earlier features exist.

### Direction (post-audit 2026-08-16)

**Out of near-term scope.** Keep as a roadmap destination. Do not drive current
architecture or requirements beyond avoiding obvious dead ends. Do not develop
until Controlled Real (015) is demonstrated and sufficient Backtest +
Simulation + controlled-Real evidence exists.

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

Status: `PLANNED` (destination; not near-term)

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
025 Stage-1 Trading Gap-Close  │
        │                      │
        ▼                      │
   MVP-1 validation gate       │
        │                      │
        ▼                      │
015 Confirmed Real Execution   │
        │                      │
        └──────────┬───────────┘
                   ▼
          016 Torque Program Core
              (includes min. composition; 018 merge direction)
                   │
                   ▼
          019 GE Search (+ min. 021 train/val/test)
                   │
                   ├── 017 Torque Capital  (DEFERRED)
                   ├── 018 richer composition (after 016 MVP if needed)
                   ├── 020 Experiment UI   (DEFERRED)
                   ├── 022 Advanced Fitness (DEFERRED)
                   ├── 023 Regime           (DEFERRED)
                   ▼
          024 Autonomous Real Trading (destination only)
```

This diagram describes the preferred development path.

Not every feature is technically dependent on every feature immediately above
it.

Feature **025** executes **before** Feature **015** despite the higher numeric
ID (IDs preserved to avoid renumbering).

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

- Feature **025** Stage-1 Trading Gap-Close must be DONE (per-position TP/SL,
  bounded strategies, intentional Sim/Backtest semantics documented);
- MVP-1 validation gate must pass (or only residual defects scheduled);
- execution abstraction must work;
- private XT integration must work (read path);
- Risk must remain authoritative;
- capital must be explicit;
- emergency stop must be tested;
- Feature 014 recovery remains available (frozen — no new recovery program).

---

## Gate B — Before GE

Before Feature 019:

- Torque programs must execute deterministically (016 MVP including simple
  composition);
- Torque must reuse Backtest;
- capital remains under Risk/Portfolio for Torque v1 (017 deferred);
- strategy composition semantics must be specified (in 016);
- evaluation configuration must be persistable at least enough for
  reproducibility (full 020 UI deferred);
- simple chronological train/validation/test accompanies first GE (021 min).

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

Feature 024 remains **out of near-term scope** until the above evidence exists.

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
007 → DONE (freeze polish)
008 → DONE (freeze expansion)
009 → DONE (freeze allocation expansion; no Portfolio redesign phase before 015)
010 → DONE (freeze weight/advanced portfolio-risk expansion)
011 → DONE
012 → DONE
013 → DONE
014 → DONE (freeze recovery expansion)
```

Current active milestone:

```text
025 → Stage-1 Trading Gap-Close   (next; before 015)
```

Then:

```text
MVP-1 validation gate (acceptance/convergence — not a feature)
        ↓
015 → Real-Money Manual/Confirmed Execution (MVP-2)
        ↓
016 → Torque MVP (composition; 018 merge direction)
        ↓
019 → GE (+ minimum 021)
```

Deferred / destination (do not drive near-term work):

```text
017 Torque Capital Allocation — DEFER
018 as separate phase — MERGE into 016 (keep ID)
020 rich experiment UI — DEFER
022 Advanced Fitness — DEFER
023 Regime — DEFER
024 Autonomous Real — destination only
```

The near-term objective is therefore:

```text
close Stage-1 trading gaps (025)
        ↓
validate Backtest → Simulation (MVP-1 gate)
        ↓
controlled Real with confirmation (015)
        ↓
compose with Torque (016)
        ↓
search with minimal GE (019 + 021 min)
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
Close Stage-1 gaps (TP/SL, strategies, semantics)
  ↓
Trade with Confirmation
  ↓
Compose with Torque
  ↓
Search with GE
  ↓
Validate Out-of-Sample
  ↓
Automate Carefully (destination)
```