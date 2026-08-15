# CryptoAutoTrading — Project Proposal

**Version:** 2.0  
**Date:** 2026-08-12  
**Primary Exchange:** XT.COM  
**Development Method:** Spec-Driven Development with GitHub Spec Kit  
**Backend:** Python / FastAPI  
**Frontend:** React / TypeScript  
**Initial Database:** SQLite  
**Future Database:** PostgreSQL  
**Initial Deployment:** Local development environment  
**Future Deployment:** Server / controlled production environment  
**Initial Trading Mode:** Simulation  
**Long-Term Direction:** Controlled automated trading + Torque + Grammatical Evolution

---

## 1. Project Vision

CryptoAutoTrading is a simulation-first, evidence-driven cryptocurrency trading and research platform for designing, testing, comparing, composing, evolving, and eventually executing controlled trading programs.

The project is based on a fundamental separation between:

- trading intelligence,
- permission to trade,
- risk control,
- capital management,
- and execution.

A strategy, Torque program, optimization method, machine-learning model, sentiment model, or Grammatical Evolution system may propose what the system should do, but none of these components has direct authority to move money.

All trading actions must pass through the same controlled trading pipeline.

The long-term objective is broader than finding a single profitable technical indicator. CryptoAutoTrading will investigate whether combinations of:

- trading strategies,
- strategy parameters,
- time segmentation,
- capital allocation,
- signal composition,
- market regimes,
- and eventually evolved trading programs

can produce robust performance after realistic costs and risk are considered.

The first exchange is XT.COM. Development begins with historical backtesting and simulated funds. Real-money capabilities are introduced incrementally and remain explicitly gated.

---

## 2. Core Architectural Principle

The central architecture is:

```text
Market Data
    ↓
Trading Intelligence
    ↓
BUY / SELL / HOLD intentions
    ↓
Trading Controller
    ↓
Risk Manager
    ↓
Capital / Portfolio Authority
    ↓
Execution
    ↓
Historical / Simulation / Real
    ↓
Accounting & P&L
    ↓
Decision / Trade Journal
```

The key rule is:

> **Trading intelligence proposes; Controller and Risk decide; Execution acts.**

Strategies are advisory only.

Torque is advisory only.

Grammatical Evolution is advisory only.

Future AI or sentiment systems are advisory only.

None may bypass:

```text
Controller → Risk → Execution
```

Torque and GE must not become second trading engines.

---

## 3. Product and Research Objectives

CryptoAutoTrading has two complementary purposes.

### 3.1 Trading Platform

The system should allow an operator to:

- Monitor cryptocurrency markets.
- Configure simulation sessions.
- Run historical backtests.
- Select registered trading strategies.
- Configure strategy parameters.
- Compare strategies fairly.
- Define available and allocated capital.
- Control position sizes.
- Define profit and loss boundaries.
- Inspect every trading decision.
- Inspect trades and performance.
- Manage portfolio exposure.
- Connect safely to XT private APIs.
- Progress from simulation to controlled real trading.
- Eventually enable autonomous trading only after explicit safety gates.

### 3.2 Trading Research Platform

The system should also support systematic experimentation.

It should eventually answer questions such as:

- Which strategies work best for particular markets?
- Which parameter configurations are robust?
- Does one strategy dominate across time, or should strategies change?
- Can capital be divided effectively between several strategies?
- Can multiple strategy signals be combined?
- Can different strategies be used during different periods?
- Can a grammar describe these trading programs?
- Can Grammatical Evolution discover useful programs?
- Do evolved programs outperform conventional strategies?
- Do they outperform buy-and-hold after costs?
- Are results robust out of sample?
- Does market-regime information improve performance?

---

## 4. Trading Intelligence Layers

CryptoAutoTrading will progressively support several levels of trading intelligence.

### 4.1 Conventional Strategies

Strategies implement a common interface and produce:

```text
BUY
SELL
HOLD
```

The current strategy framework includes:

- Dual EMA
- RSI
- MACD
- Bollinger Bands
- Breakout

Each strategy has:

- a stable strategy identifier,
- parameter definitions,
- default values,
- validation constraints,
- minimum history requirements,
- deterministic signal-generation behavior.

For example:

```text
Dual EMA
fastPeriod = 9
slowPeriod = 21
```

or:

```text
RSI
period = 14
oversold = 30
overbought = 70
```

Strategy parameters are configuration, not strategy identity.

### 4.2 Strategy Comparison

Before introducing optimization or evolution, the platform supports controlled comparison of conventional strategies.

A comparison uses common experimental conditions:

```text
Same symbol
Same timeframe
Same historical window
Same market candles
Same capital assumptions
Same fees
Same slippage
Same execution rules
```

while varying:

```text
Strategy
Strategy parameters
```

This provides a trustworthy baseline for later Torque and GE experiments.

### 4.3 Torque Trading Programs

Torque introduces programmable composition above individual strategies.

A Torque trading program may eventually describe:

- which strategy to use,
- which parameters to use,
- when to use it,
- how much capital to allocate,
- how several strategies interact,
- how signals are composed.

Conceptually, a sequential program might represent:

```text
Period 1:
    RSI(period=14, oversold=30, overbought=70)

Period 2:
    MACD(fastPeriod=12, slowPeriod=26, signalPeriod=9)

Period 3:
    Breakout(lookback=20)
```

A capital-allocation program could represent:

```text
500 USDT total

250 USDT → RSI(...)
250 USDT → MACD(...)
```

Both strategies may operate over the same period while respecting their allocated capital.

More sophisticated Torque programs may later combine sequential and parallel behavior.

The exact Torque grammar and semantics will be specified incrementally rather than prematurely fixed.

### 4.4 Grammatical Evolution

Grammatical Evolution will search the space of valid Torque trading programs.

Conceptually:

```text
Genotype
    ↓
Grammar Mapping
    ↓
Torque Trading Program
    ↓
Historical Trading Pipeline
    ↓
Performance Evaluation
    ↓
Fitness
```

The grammar defines the legal search space.

GE therefore does not generate arbitrary exchange operations. It generates valid trading programs that still execute through the established controlled infrastructure.

---

## 5. Operating Modes

The platform separates historical evaluation, simulation, and real execution.

### 5.1 Historical Backtesting

Historical backtesting evaluates trading behavior against previously recorded market candles.

It must:

- never place exchange orders,
- use deterministic historical execution semantics,
- include fees and slippage,
- maintain capital and positions,
- record decisions,
- record trades,
- calculate liquidation-consistent equity,
- calculate drawdown,
- compare performance against buy-and-hold.

Historical execution uses its own execution adapter rather than pretending to be live simulation.

For example, a signal generated from closed candle N may execute using the defined historical fill rule at candle N+1.

### 5.2 Simulation

Simulation uses current market information but virtual capital.

It models:

- cash,
- positions,
- quantity,
- fills,
- fees,
- slippage,
- realized P&L,
- unrealized P&L,
- net P&L,
- portfolio equity.

Simulation is the primary environment for validating trading behavior before real money.

### 5.3 Controlled Real Trading

Real trading is introduced only after simulation, backtesting, portfolio, risk, execution abstraction, XT private API integration, and live paper-trading hardening are mature.

Initial real trading should be deliberately constrained.

For example:

```text
Spot only
Small dedicated capital
Explicit operator confirmation
Strict maximum exposure
Strict loss limits
Emergency stop
Complete journaling
```

Autonomous real-money trading is a separate, much later milestone.

---

## 6. Execution Abstraction

Trading logic should not know whether an approved trading action will be executed historically, in simulation, or on an exchange.

Conceptually:

```text
                  ┌─ HistoricalExecutionAdapter
Trading Intent ───┼─ SimulationExecutionAdapter
                  └─ RealExecutionAdapter
```

Each adapter has different execution semantics while preserving common accounting and control principles.

Historical execution may fill against future historical candle information according to explicit backtesting rules.

Simulation execution models current-market fills.

Real execution communicates with XT and reconciles actual exchange order state.

This abstraction is critical because Torque and GE should be able to reuse the same trading infrastructure.

---

## 7. Trading Controller

The Trading Controller is an authority boundary.

For every non-HOLD trading intention it determines whether execution may proceed.

Checks may include:

- Is trading currently permitted?
- Is the session active?
- Has the profit target been reached?
- Has the maximum loss been reached?
- Has the trade limit been reached?
- Is sufficient capital available?
- Would the trade exceed allocation?
- Would the trade exceed position limits?
- Would it violate portfolio exposure limits?
- Is the strategy in warm-up?
- Is market data valid and sufficiently recent?
- Is execution available?
- Is a cooldown active?
- Is an emergency stop active?
- Is real-money automation explicitly permitted?

Only approved intentions reach execution.

---

## 8. Risk Management

Risk rules always have higher authority than strategy signals.

Initial controls include:

- Allocated-capital limit
- Maximum position size
- Session profit target
- Session loss limit
- Maximum strategy trades
- Emergency stop

Advanced controls may include:

- Per-position stop-loss
- Per-position take-profit
- Trailing stop
- Consecutive-loss limits
- Loss cooldown
- Maximum daily drawdown
- Portfolio exposure limits
- Strategy-specific allocation limits
- Correlated-position limits
- Real-money execution limits

Risk management must remain independent of individual strategy implementations.

---

## 9. Portfolio and Capital Authority

Capital becomes increasingly important as the system moves from single strategies toward Torque programs.

The portfolio layer should become the authoritative source for:

- available cash,
- allocated cash,
- reserved capital,
- holdings,
- positions,
- realized P&L,
- unrealized P&L,
- total equity,
- strategy allocations,
- aggregate exposure.

For example:

```text
Total available capital: 500 USDT

Torque Program:
    RSI allocation:       200 USDT
    MACD allocation:      200 USDT
    Reserve:              100 USDT
```

No strategy may spend capital simply because its signal says BUY.

Capital allocation must be explicitly approved and enforced.

This is required before meaningful parallel Torque programs can be implemented.

---

## 10. Trading and Experiment Defaults

The application will contain configurable defaults for frequently repeated values.

Potential defaults include:

- Preferred symbol
- Preferred timeframe
- Starting capital
- Allocated capital
- Position size
- Fee assumptions
- Slippage assumptions
- Profit/loss limits
- Strategy defaults
- Backtesting defaults
- Future experiment defaults

However:

> **Settings are defaults only.**

Every actual simulation, backtest, comparison, Torque experiment, GE experiment, and real trading session must persist the effective configuration that was actually used.

Changing settings must never change the historical meaning of an existing run.

---

## 11. Strategy Parameters and Reproducibility

Every trading run should preserve enough information to reproduce its behavior.

For example:

```json
{
  "strategyId": "dual_ema",
  "strategyParams": {
    "fastPeriod": 9,
    "slowPeriod": 21
  }
}
```

The same principle applies later to Torque and GE.

An experiment should eventually preserve:

- strategy/program,
- effective parameters,
- capital configuration,
- symbol,
- timeframe,
- historical window,
- fee assumptions,
- slippage assumptions,
- risk configuration,
- random seed where applicable,
- grammar version,
- evolutionary configuration,
- software/experiment metadata where useful.

Reproducibility is a core research requirement.

---

## 12. Backtesting and Performance Evaluation

Backtesting is not merely a visual feature. It is the main experimental execution environment.

Important metrics include:

- Starting capital
- Ending capital
- Net P&L
- Net return
- Buy-and-hold return
- Number of fills
- Number of round trips
- Win rate
- Maximum drawdown
- Best trade
- Worst trade
- Fees
- Slippage
- Equity trajectory

Later research metrics may include:

- Sharpe-like risk-adjusted measures
- Sortino ratio
- Profit factor
- Exposure
- Turnover
- Downside risk
- Stability across periods
- Generalization performance

All comparisons must account for realistic costs.

---

## 13. Fitness Functions

A future GE experiment needs an explicit objective.

A useful initial fitness formulation is:

\[
F(P)=R_P-R_{BH}
\]

where:

- P is a trading program,
- R_P is the program's net return,
- R_BH is buy-and-hold return over the identical evaluation period.

This asks:

> How much value did the trading program add relative to simply buying and holding?

However, this should not permanently define the project.

Pure return can reward undesirable behavior such as excessive drawdown or fragile overfitting.

Later fitness functions may therefore incorporate:

\[
F(P)=
\text{Return}
-\lambda_1\text{Drawdown}
-\lambda_2\text{TradingCost}
-\lambda_3\text{Complexity}
\]

or use true multi-objective optimization.

Candidate objectives include:

- Net return
- Excess return over buy-and-hold
- Maximum drawdown
- Trading cost
- Stability
- Program complexity
- Out-of-sample performance

Fitness definitions must be explicit and versioned with experiments.

---

## 14. Train / Validation / Test Evaluation

A major research risk is overfitting historical market data.

Selecting the best strategy or evolved program using the same period on which final performance is reported would provide weak evidence.

Future experiments should therefore support chronological separation such as:

```text
Historical Data
│
├── Training period
│      GE searches programs
│
├── Validation period
│      model/program selection
│
└── Test period
       final unseen evaluation
```

Where appropriate, rolling or walk-forward evaluation may later be added.

The final test period must not influence evolutionary search.

This distinction is essential when claiming that Torque or GE improves trading performance.

---

## 15. Market Regimes

A single trading program may not be optimal across all market conditions.

Future regime-aware research may distinguish:

- Strong uptrend
- Weak uptrend
- Downtrend
- Sideways market
- High volatility
- Low volatility

Torque could eventually represent behavior such as:

```text
IF regime = trend:
    Breakout(...)

IF regime = sideways:
    BollingerBands(...)

IF regime = high_volatility:
    reduce capital allocation
```

GE could then evolve regime-aware programs.

Regime detection is deliberately deferred until conventional strategies, Torque, and experimental evaluation are reliable.

---

## 16. Decision and Trade Journaling

Every meaningful strategy evaluation should be traceable.

A Decision Record may contain:

```text
Time:        13:42
Pair:        BTC/USDT
Strategy:    RSI
Parameters:  period=14, oversold=30, overbought=70
Signal:      BUY
Decision:    REJECTED
Reason:      Maximum position size reached
```

Possible decision states include:

```text
HOLD
APPROVED
REJECTED
APPROVED_UNEXECUTABLE
FORCED
```

Executed actions create Trade Records containing relevant information such as:

- price,
- quantity,
- fees,
- slippage,
- timestamps,
- strategy/program,
- mode,
- capital impact,
- resulting P&L.

The system should be able to reconstruct why an action occurred or did not occur.

This requirement applies equally to conventional strategies, Torque programs, and evolved programs.

---

## 17. User Interface

CryptoAutoTrading retains three primary application areas:

```text
Dashboard
Auto Trading
Portfolio
```

The application should not grow a new top-level navigation item for every research feature.

### 17.1 Dashboard

Purpose: understand the current market and system state.

Potential components:

- Selected cryptocurrency prices
- Price changes
- Volume
- Charts
- Volatility
- Market context
- Important news
- Sentiment information
- Active trading status
- Portfolio summary

### 17.2 Auto Trading

Auto Trading is the main trading workspace.

It can contain internal sections/tabs such as:

```text
Simulation
Backtest
Comparison
Real Trading
```

and later appropriate research surfaces.

Simulation configuration includes:

- Symbol
- Timeframe
- Strategy
- Strategy parameters
- Capital
- Risk boundaries
- Session boundaries

Backtesting includes:

- Historical window
- Strategy
- Parameters
- Capital
- Fees/slippage
- Performance results
- Trades
- Decisions

Strategy Comparison allows several strategy/parameter configurations to be evaluated under identical historical conditions.

### 17.3 Portfolio

Portfolio provides the capital and performance view.

It may include:

- Available balance
- Allocated capital
- Holdings
- Open positions
- Portfolio equity
- Unrealized P&L
- Realized P&L
- Exposure
- Trading history
- Performance history
- Strategy/program attribution

Simulation and real portfolios must always be visibly distinguishable.

---

## 18. Responsive Design

The application is responsive from the beginning.

Primary workflows should remain usable around phone width (~375 px).

Important mobile actions include:

- Check trading status
- Inspect P&L
- Inspect portfolio
- Start simulation
- Stop simulation
- Activate emergency stop
- Inspect decisions
- Inspect trades
- Inspect backtest results

A native mobile application is not initially required.

---

## 19. Technical Architecture

### Frontend

**React + TypeScript**

Responsibilities include:

- Responsive UI
- Trading configuration
- Dynamic strategy configuration
- Charts
- Backtesting interface
- Comparison interface
- Portfolio visualization
- Session monitoring
- Experiment inspection

### Backend

**Python + FastAPI**

Responsibilities include:

- Market data
- Strategy registry
- Strategy evaluation
- Controller
- Risk
- Capital allocation
- Portfolio
- Historical execution
- Simulation execution
- Real execution
- Backtesting
- Accounting
- Journaling
- XT integration
- Torque execution
- GE experiment orchestration
- Reporting

### Database

Initial:

**SQLite**

Future deployment:

**PostgreSQL**

SQLAlchemy provides persistence abstraction.

### Exchange Boundary

XT-specific implementation must remain behind adapter boundaries.

Public market data and authenticated account/trading APIs should remain separated where practical.

Private credentials must never leak into strategy, Torque, GE, or frontend layers.

---

## 20. Security and Real-Money Safety

Exchange credentials must:

- exist only on the backend,
- never be committed to Git,
- never appear in frontend code,
- use secure secret configuration,
- have minimum necessary permissions,
- exclude withdrawal capability.

Real-money trading must be explicitly enabled.

A configuration change must never silently transition simulation into real-money execution.

Initial real trading should require explicit confirmation.

Autonomous real-money trading requires additional safety evidence and is intentionally the final major roadmap stage.

---

## 21. Testing Strategy

Trading-critical logic requires automated testing.

### Unit Tests

Particularly for:

- Strategies
- Indicators
- Parameter validation
- Controller rules
- Risk calculations
- Capital allocation
- Position sizing
- Accounting
- P&L
- Execution fill mathematics
- Portfolio calculations
- Torque semantics
- GE mapping and fitness

### Contract Tests

For:

- Strategy API
- Simulation API
- Backtest API
- Comparison API
- Portfolio API
- Future real-trading API

### Integration Tests

For:

- Strategy → Controller → Risk → Execution
- Simulation
- Backtesting
- Portfolio/accounting
- XT integration
- Torque → existing trading pipeline
- GE → Torque → backtesting

### Regression Tests

Important established behavior must remain stable as later layers are introduced.

In particular, introducing Torque or GE must not alter existing conventional-strategy behavior.

---

## 22. Current Development Roadmap

```text
FOUNDATION

001  Application Foundation                  DONE
002  Market Data                             DONE


CONTROLLED TRADING

003  Simulation Trading Core                 DONE
004  Backtesting Core                        DONE


STRATEGY LAYER

005  Strategy Framework                      DONE
006  Additional Strategies                   DONE
007  Strategy Comparison


TRADING INFRASTRUCTURE

008  Trading & Experiment Defaults
009  Portfolio & Capital Allocation Core
010  Advanced Risk Management
011  Simulation History & Results
012  Execution Abstraction


CONTROLLED LIVE TRADING

013  XT Account / Private API Integration
014  Live Paper-Trading Hardening
015  Real-Money Manual/Confirmed Execution


TORQUE PROGRAMMABLE TRADING

016  Torque Trading Program Core
017  Torque Capital Allocation
018  Torque Signal Composition


EVOLUTIONARY SEARCH

019  Grammatical Evolution Search
020  Evolution Experiments & Results
021  Train / Validation / Test
022  Advanced Fitness
023  Regime-Aware Programs


AUTONOMOUS TRADING

024  Autonomous Real-Money Trading
```

This sequence is intentional.

The project first establishes reliable trading infrastructure.

Then it establishes controlled real execution.

Only after those foundations are mature does Torque introduce programmable trading composition.

GE is introduced only after Torque has deterministic semantics and reliable backtesting.

Autonomous real-money trading remains last.

---

## 23. Torque Research Direction

Torque is intended to provide a compact program representation for trading behavior.

A future grammar may permit GE to generate expressions representing strategy selection and composition.

Conceptually:

```text
<program> ::= <strategy>
            | <sequence>
            | <allocation>
            | <composition>
```

with strategies such as:

```text
RSI(...)
MACD(...)
BollingerBands(...)
Breakout(...)
DualEMA(...)
```

The program space may eventually describe two important dimensions.

### Temporal Composition

Different strategies may operate during different periods:

```text
t0 ───────── t1 ───────── t2

      RSI          MACD
```

### Capital Composition

Several strategies may operate simultaneously using different allocations:

```text
                 500 USDT
                    │
           ┌────────┴────────┐
           │                 │
       250 USDT          250 USDT
           │                 │
          RSI               MACD
```

Later programs may combine both.

For example:

```text
Period A:
    60% RSI
    40% MACD

Period B:
    30% Breakout
    70% Dual EMA
```

The exact syntax and semantics will be specified during Features 016–018.

---

## 24. Grammatical Evolution Research Direction

GE treats a trading program as an individual.

A genotype maps through a grammar to a valid Torque phenotype.

Conceptually:

```text
Integer Genotype
      ↓
Grammar
      ↓
Torque Program
      ↓
Historical Evaluation
      ↓
Fitness
```

Evolution may therefore search simultaneously over:

- strategy selection,
- strategy parameters,
- temporal structure,
- capital allocation,
- signal composition.

This creates a substantially richer search space than ordinary indicator parameter optimization.

However, increased expressive power also increases overfitting risk.

Therefore GE experiments require:

- deterministic evaluation,
- fixed datasets/windows,
- reproducible configurations,
- explicit fitness definitions,
- train/validation/test separation,
- conventional-strategy baselines,
- buy-and-hold baseline,
- realistic fees/slippage,
- risk reporting.

---

## 25. Development Method

CryptoAutoTrading follows Spec-Driven Development using GitHub Spec Kit.

The authoritative governance order is:

```text
Constitution
     ↓
Roadmap
     ↓
Feature Specification
     ↓
Clarification
     ↓
Implementation Plan
     ↓
Tasks
     ↓
Specification Analysis
     ↓
Implementation
     ↓
Tests
     ↓
Quickstart / Smoke Validation
     ↓
Convergence
     ↓
Documentation
     ↓
Roadmap Update
     ↓
Git Commit
```

The Constitution defines architectural rules.

The Roadmap defines sequencing.

Feature specifications define intended behavior.

Plans define technical design.

Tasks define implementation work.

Code is not considered complete merely because it compiles or passes a narrow test.

A feature becomes DONE only after its completion gate is satisfied.

---

## 26. Current Product State

The original MVP objective was:

> Execute one automated simulated trading session end-to-end under explicit risk controls.

That milestone has evolved substantially.

The platform now has foundations for:

- Market data
- Simulation trading
- Historical backtesting
- Shared strategy framework
- Multiple conventional strategies
- Strategy parameters
- Historical performance metrics
- Decision journaling
- Trade journaling

The immediate development focus is completing controlled strategy comparison and then strengthening shared trading infrastructure before introducing Torque.

---

## 27. Near-Term Development Priorities

The immediate sequence is:

```text
007 Strategy Comparison
        ↓
008 Trading & Experiment Defaults
        ↓
009 Portfolio & Capital Allocation
        ↓
010 Advanced Risk Management
        ↓
011 Simulation History & Results
        ↓
012 Execution Abstraction
```

These features are important before Torque.

In particular, Torque capital allocation should not invent its own wallet or accounting system. It should reuse Feature 009.

Torque should not invent its own risk system. It should reuse Feature 010.

Torque should not invent historical/simulation/real execution. It should reuse Feature 012.

This reuse is a central architectural objective.

---

## 28. Long-Term Research Questions

CryptoAutoTrading should eventually provide evidence for questions including:

- Which conventional strategies outperform buy-and-hold after costs?
- How sensitive are strategies to their parameters?
- How stable are strategy rankings across market periods?
- Does changing strategies through time outperform a fixed strategy?
- Does parallel capital allocation across strategies improve risk-adjusted performance?
- Which strategy combinations are complementary?
- Can Torque represent useful trading structures compactly?
- Can GE discover better Torque programs than manually designed ones?
- How much of GE's apparent improvement survives unseen test data?
- Does penalizing drawdown improve robustness?
- Does penalizing program complexity reduce overfitting?
- Which evolved structures generalize across cryptocurrencies?
- Are different programs required for different market regimes?
- Does sentiment provide measurable incremental value?
- Can evolved programs outperform simple baselines consistently after realistic fees and slippage?
- What evidence is sufficient before allowing an evolved program to control real capital?

---

## 29. Non-Goals and Safety Boundaries

The project does not initially target:

- High-frequency trading
- Futures
- Margin
- Leverage
- Short selling
- Exchange withdrawals
- Unbounded autonomous trading
- Guaranteed profit
- Black-box AI execution
- Strategy-controlled order placement

Backtesting success is evidence, not proof of future profitability.

Optimization success is evidence, not proof of generalization.

GE fitness is an experimental measurement, not a guarantee of future profit.

Real-money capabilities must remain more restrictive than historical and simulation capabilities.

---

## 30. Final Project Direction

CryptoAutoTrading evolves through four conceptual stages:

```text
1. CONTROL

Reliable market data
Simulation
Backtesting
Controller
Risk
Portfolio
Execution


2. COMPOSITION

Multiple strategies
Strategy comparison
Torque programs
Capital allocation
Signal composition


3. EVOLUTION

Grammatical Evolution
Experiment management
Fitness design
Train / validation / test
Regime-aware programs


4. DEPLOYMENT

XT private integration
Controlled real execution
Safety validation
Eventually autonomous trading
```

The long-term objective is not simply to create a bot that trades cryptocurrency.

It is to create a controlled experimental platform in which trading ideas can be represented, tested, compared, composed, evolved, validated, and—only after sufficient evidence and safety controls—executed using real capital.

The central invariant remains:

> **Strategies, Torque, GE, and future AI decide what they would like to do. Controller, Risk, Capital, and Execution decide what the system is actually allowed to do.**

This separation allows the research layer to become increasingly sophisticated without weakening the safety and accounting foundations underneath it.
