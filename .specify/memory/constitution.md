# CryptoAutoTrading Constitution

## Purpose

CryptoAutoTrading is a research-driven cryptocurrency trading platform designed
to support market observation, strategy development, simulation, historical
backtesting, controlled experimentation, Grammatical Evolution (GE), and,
eventually, carefully controlled real-money trading.

The system MUST evolve incrementally from observable and testable components
toward higher levels of automation.

Safety, reproducibility, traceability, and architectural consistency take
priority over rapid addition of trading features.

---

## I. Capital Protection First

Capital protection MUST take precedence over profit maximization.

Every trading mode that can modify a portfolio MUST enforce explicit risk and
capital constraints.

A strategy, Torque program, GE individual, UI component, or external service
MUST NOT bypass risk controls.

Invalid, incomplete, inconsistent, stale, or unsafe trading state MUST fail
closed.

---

## II. Simulation Before Real Money

Trading behavior MUST be validated through simulation and/or historical
backtesting before equivalent behavior becomes eligible for real-money
execution.

New strategies, execution rules, risk rules, Torque constructs, or evolved
programs MUST NOT move directly from implementation to autonomous real-money
trading.

Real-money capability MUST be introduced incrementally.

---

## III. Single Trading Pipeline

All trading decisions MUST follow the authoritative pipeline:

Market Data
    ↓
Strategy / Torque Program
    ↓
Controller
    ↓
Risk
    ↓
Execution
    ↓
Accounting / Portfolio
    ↓
Decision Journal / Reporting

No feature may create a second independent trading engine.

Strategies and Torque programs produce trading intent only.

Controller, Risk, Execution, and Accounting remain authoritative.

---

## IV. Controller and Risk Authority

Strategies are advisory only.

A strategy MAY produce BUY, SELL, or HOLD intent and diagnostics.

A strategy MUST NOT directly:

- mutate cash;
- mutate positions;
- create authoritative fills;
- bypass Controller;
- bypass Risk;
- call private exchange trading APIs.

Torque and GE-generated programs are subject to the same rule.

Controller and Risk MUST remain between generated trading intent and execution.

---

## V. Explicit Trading Boundaries

Every live or simulated trading session MUST define explicit operational
boundaries appropriate to that mode.

These MAY include:

- allocated capital;
- maximum position size;
- maximum trades;
- profit target;
- maximum loss;
- duration;
- explicit stop conditions.

Historical backtests use an explicit start/end historical window in place of a
live-session duration.

Backtest early-exit controls such as maximum trades, profit target, and maximum
loss MAY be optional when the feature specification explicitly permits it.

Historical evaluation MUST remain bounded.

---

## VI. Net Performance Is Authoritative

Trading performance MUST be evaluated using NET results after applicable costs.

Where applicable, calculations MUST include:

- fees;
- slippage;
- realized P&L;
- unrealized P&L;
- liquidation value.

Gross profit alone MUST NOT be presented as authoritative trading performance.

---

## VII. Decision Traceability

Every trading evaluation SHOULD be explainable after execution.

Trading sessions and historical runs MUST preserve sufficient information to
reconstruct important decisions.

Where applicable, persisted information SHOULD include:

- strategy or Torque program identity;
- effective parameters;
- configuration;
- signal;
- Controller decision;
- Risk decision;
- rejection reason;
- execution result;
- fees and slippage;
- resulting portfolio state.

GE experiments MUST preserve enough information to reproduce evaluated
individuals.

---

## VIII. Fail-Safe Behavior

Trading-critical failures MUST fail safely.

Examples include:

- invalid strategy;
- invalid strategy parameters;
- invalid Torque program;
- unavailable required market data;
- insufficient historical data;
- stale data where freshness is required;
- private API authentication failure;
- exchange rejection;
- inconsistent portfolio state;
- violated capital or risk constraints.

The system MUST NOT fabricate fills, prices, balances, or successful execution.

---

## IX. Emergency Stop

Real-time trading modes MUST provide a reliable emergency-stop mechanism before
autonomous real-money trading is permitted.

Stopping MUST prevent new strategy-driven entries.

Position handling during stop MUST follow the applicable feature specification
and risk rules.

Historical synchronous backtests do not require a separate emergency stop.

---

## X. Intentional Simplicity

Prefer the simplest architecture that preserves correctness, safety,
extensibility, and testability.

Do not introduce distributed systems, queues, workers, WebSockets, plugin
infrastructure, or additional persistence layers without demonstrated need.

Complexity MUST be justified by a concrete requirement.

---

## XI. Conventional Strategies First

Before introducing strategy optimization or evolutionary search, the platform
SHOULD establish a reliable set of conventional deterministic strategies.

Strategy implementations MUST use the shared Strategy contract and registry.

Simulation and Backtest MUST use the same strategy implementation.

Strategy-specific execution engines are forbidden.

---

## XII. Historical Evidence Is Not a Profit Guarantee

Backtest, comparison, experiment, and GE results are historical evidence only.

The UI and documentation MUST NOT imply guaranteed future profitability.

Optimization results MUST be treated as susceptible to overfitting.

---

## XIII. Primary Product Areas

The primary application navigation SHOULD remain intentionally small.

The principal areas are:

1. Dashboard
2. Auto Trading / Trade
3. Portfolio

Simulation, Backtest, Strategy Comparison, Torque, and related trading tools
SHOULD normally live within the Auto Trading / Trade domain rather than becoming
independent primary navigation items unless future product complexity clearly
justifies restructuring.

---

## XIV. Responsive UX

Primary operator workflows MUST remain usable on desktop and approximately
375px phone-width screens.

Trading-critical controls MUST NOT depend on hover-only interaction.

Important risk, execution, and real-money state MUST be clearly distinguishable.

---

## XV. Technology Baseline

Unless explicitly changed by an approved feature specification:

Backend:
- Python 3.12+
- FastAPI
- SQLAlchemy
- SQLite for local persistence

Frontend:
- React
- TypeScript
- Vite

Trading-domain numerical values requiring deterministic accounting SHOULD use
Decimal-safe representations rather than binary floating point.

---

## XVI. Exchange Isolation

Exchange-specific behavior MUST remain behind adapters.

Core strategy, Controller, Risk, Backtest, Torque, GE, and accounting logic
MUST NOT depend directly on XT-specific types.

---

## XVII. Public and Private Exchange Separation

Public market-data access and private account/trading access MUST remain
separate concerns.

Features requiring only public market data MUST NOT require exchange
credentials.

---

## XVIII. Credential Safety

Exchange credentials MUST NOT be committed to source control.

Private credentials MUST be loaded through an approved local configuration or
secret mechanism.

Real-money permissions SHOULD follow least privilege.

Withdrawal permission SHOULD NOT be required for automated trading.

---

## XIX. Sentiment Is Advisory

Market sentiment, news analysis, social signals, or external AI-derived signals
MAY influence trading intent in future features.

They MUST NOT directly execute trades or bypass Controller and Risk.

---

## XX. External Information Must Be Traceable

Where external news, sentiment, or analytical sources influence decisions, the
system SHOULD retain source identity, timestamp, and relevant derived signal
where practical.

---

## XXI. Stale External Signals Must Be Detectable

Time-sensitive external signals MUST carry sufficient timestamp/freshness
information to prevent silently treating stale information as current.

---

## XXII. Missing Sentiment Must Not Fabricate Confidence

If sentiment or news data is unavailable, the system MUST represent that state
explicitly rather than inventing a neutral, positive, or negative signal.

---

## XXIII. Sentiment Must Not Override Risk

No sentiment score, news event, model output, or confidence value may override
capital or risk constraints.

---

## XXIV. Sentiment Integration Must Be Testable

Any future sentiment-to-trading mapping MUST have deterministic interfaces that
can be tested independently from external providers.

---

## XXV. Sentiment Providers Must Be Replaceable

Provider-specific APIs SHOULD remain behind adapters or service boundaries so
the trading pipeline does not depend on a single external provider.

---

## XXVI. Sentiment and News Are Not Execution Engines

Sentiment/news components MAY generate features, scores, classifications, or
trading intent.

They MUST NOT become independent execution paths.

---

## XXVII. Specification-Driven Development

Material features MUST be specified before implementation.

Feature documentation SHOULD normally include:

- `spec.md`
- `plan.md`
- `research.md` where needed
- `data-model.md` where needed
- `contracts/` where applicable
- `quickstart.md`
- `tasks.md`

Clarifications MUST be reflected in the specification before implementation
when they materially affect behavior.

Later explicit clarifications take precedence over older conflicting wording.

---

## XXVIII. Trading-Critical Automated Tests

Trading-critical behavior MUST have automated tests.

Depending on the feature, tests MUST cover relevant areas such as:

- strategy signals;
- parameter validation;
- Controller behavior;
- Risk rejection;
- fill timing;
- fees and slippage;
- accounting;
- capital constraints;
- stop behavior;
- duplicate-candle prevention;
- determinism;
- historical metrics;
- persistence;
- API contracts;
- pipeline isolation.

A trading-critical feature MUST NOT be considered complete solely because its
UI works manually.

---

## XXIX. Behavioral Continuity

Refactoring shared trading infrastructure MUST preserve previously specified
behavior unless a new specification intentionally changes it.

Regression tests SHOULD protect important established behavior.

Shared implementations SHOULD be preferred over forks.

---

## XXX. Git Traceability

Feature implementation SHOULD remain traceable through Git history.

Feature work SHOULD use meaningful commits referencing the relevant feature or
scope.

Automated tools MAY propose commit messages but MUST NOT commit automatically
unless explicitly instructed by the operator.

---

## XXXI. Roadmap Synchronization

The project roadmap at `core/roadmap.md` MUST remain synchronized with the
actual implementation state of the repository.

Every planned material feature MUST have a roadmap entry.

The standard roadmap states are:

- `PLANNED`
- `IN PROGRESS`
- `BLOCKED`
- `DEFERRED`
- `DONE`

Creating a feature specification MUST add or update its roadmap entry.

Starting implementation SHOULD change the corresponding feature to
`IN PROGRESS`.

A feature MUST NOT be marked `DONE` merely because implementation code exists.

A feature may be marked `DONE` only after:

1. required implementation is complete;
2. required automated tests pass;
3. specification/implementation analysis or convergence has no unresolved
   blocking issue;
4. required documentation is updated;
5. required quickstart/smoke validation is complete.

When a feature reaches `DONE`, the implementation/completion workflow MUST
update `core/roadmap.md`.

If a completed feature changes the scope, prerequisites, dependencies, or
ordering of later work, the roadmap MUST be reviewed and updated.

The roadmap records direction, sequencing, dependency, and status.

Detailed behavioral requirements remain authoritative in the corresponding
`specs/NNN-*/` documentation.

---

## XXXII. Execution Abstraction

Execution behavior MUST be abstracted from decision generation.

The system SHOULD support execution implementations appropriate to mode, such
as:

- HistoricalExecutionAdapter
- SimulationExecutionAdapter
- RealExecutionAdapter

Controller and Risk SHOULD operate independently of the concrete execution
adapter.

Historical, simulation, and real trading MUST NOT require separate strategy
engines.

---

## XXXIII. Settings Are Defaults, Not Historical Truth

Application settings MAY provide reusable operator defaults.

Settings MUST NOT silently alter already-created trading sessions, backtests,
comparisons, Torque programs, or experiments.

At creation time, effective configuration MUST be materialized and persisted
with the run/session where reproducibility requires it.

Changing a default affects future configurations only unless the operator
explicitly edits an allowed configuration.

---

## XXXIV. Portfolio and Capital Allocation Authority

Capital allocation MUST be represented explicitly rather than being hidden
inside strategies.

Multiple strategies or Torque program branches MAY operate over separate
allocations, but total allocation MUST respect available capital and global
risk constraints.

Strategies MUST NOT independently create or invent capital.

Portfolio/accounting state remains authoritative.

---

## XXXV. Torque Is a Trading Program Layer, Not a Second Engine

Torque may describe compositions of strategies, parameters, time windows,
capital allocations, and signal-composition logic.

Torque programs MUST ultimately produce trading intent that enters the same:

Controller → Risk → Execution → Accounting

pipeline used by conventional strategies.

Torque MUST NOT directly mutate balances or positions or call exchange trading
APIs.

The Torque language and grammar SHOULD remain sufficiently general for
Grammatical Evolution to generate valid programs.

---

## XXXVI. Grammatical Evolution Searches Programs, Not Execution Paths

Grammatical Evolution MAY search over valid Torque programs, strategy choices,
strategy parameters, capital allocation, temporal composition, and other
explicitly permitted grammar constructs.

GE MUST NOT generate code that bypasses the authoritative trading pipeline.

Every evaluated individual MUST be reproducible from its genotype, grammar,
effective configuration, market-data window, and evaluation settings.

---

## XXXVII. Fitness Must Be Explicit and Reproducible

Every evolutionary experiment MUST define its fitness function explicitly.

Fitness inputs and evaluation data MUST be persisted or reproducibly
identifiable.

A baseline such as Buy & Hold MAY be incorporated into fitness.

For example, an initial Torque trading fitness may use:

    fitness = strategy_program_net_profit - buy_and_hold_net_profit

but future specifications MAY extend this with risk, drawdown, robustness,
turnover, or other objectives.

Fitness MUST use cost-aware results when the evaluated trading path incurs
fees or slippage.

---

## XXXVIII. Prevent Optimization Leakage

Training/optimization data MUST be distinguishable from validation and final
test data before claims about evolved trading quality are made.

GE MUST NOT select individuals using final test-period performance.

Future Train / Validation / Test features MUST preserve this separation.

---

## XXXIX. Real-Money Automation Requires Explicit Enablement

Real-money automated trading MUST be disabled by default.

Real-money capability MUST require explicit operator enablement and clearly
distinguishable UI state.

Before autonomous real-money trading is allowed, the system MUST have:

- private exchange integration;
- execution abstraction;
- account reconciliation;
- capital allocation controls;
- risk controls;
- emergency stop;
- deterministic decision traceability;
- failure/retry handling;
- tested simulation/paper behavior;
- explicit real-money configuration.

A backtest, simulation, strategy comparison, Torque result, or GE result MUST
never automatically activate real-money trading.

---

## XL. Reuse Before Duplication

New trading features MUST reuse established domain components where their
semantics match.

In particular, future Torque and GE functionality SHOULD reuse:

- market data;
- strategy registry;
- Controller;
- Risk;
- execution adapters;
- accounting;
- portfolio/capital allocation;
- backtesting;
- decision journals;
- metrics.

Duplicating these components specifically for Torque/GE requires explicit
justification.

---

## Governance

This constitution is the highest-level engineering and product governance
document for CryptoAutoTrading.

Feature specifications MUST comply with it.

If a feature conflicts with a MUST rule, one of the following is required
before implementation:

1. change the feature specification;
2. amend the constitution intentionally; or
3. document an explicit approved exception if the constitution permits one.

A plan MUST NOT mark a constitution gate as PASS by informally weakening a
MUST requirement.

Constitution amendments SHOULD explain why the architectural or product rule
changed.

Detailed implementation decisions belong in feature specifications and design
documents rather than being added to this constitution unless they represent
durable project-wide rules.