# MyCrypto --- Project Proposal

**Version:** 1.0\
**Date:** 2026-08-08\
**Primary Exchange:** XT.COM\
**Development Method:** Spec-Driven Development with GitHub Spec Kit\
**Backend:** Python / FastAPI\
**Frontend:** React\
**Initial Database:** SQLite\
**Future Database:** PostgreSQL\
**Initial Deployment:** Local laptop\
**Future Deployment:** Server\
**Primary Initial Mode:** Simulation

## 1. Project Vision

MyCrypto is a simple, responsive cryptocurrency monitoring and
automated-trading platform designed primarily to enforce disciplined,
rule-based trading behavior.

The project does **not** assume that emotional control alone guarantees
profitability. Its core hypothesis is that systematic execution,
explicit risk limits, controlled position sizing, and evidence-based
strategy evaluation can reduce impulsive trading decisions and make
trading behavior measurable and reproducible.

The first target exchange is XT.COM. Development begins entirely with
simulated funds. Real-money trading is a later capability and must pass
explicit safety and acceptance criteria before activation.

## 2. Core Product Principle

The architecture separates a strategy's recommendation from permission
to execute it.

``` text
Market Data
    ↓
Strategy Engine
    ↓
BUY / SELL / HOLD
    ↓
Trading Controller
    ↓
Risk Manager
    ↓
Execution Engine
    ↓
Simulation / XT
    ↓
Portfolio & P&L
    ↓
Continue / Stop
```

**The strategy proposes; the controller decides.**

Strategies must never place exchange orders directly.

## 3. Primary Objectives

The system will allow the user to:

-   Select a supported cryptocurrency pair such as BTC/USDT, ETH/USDT,
    or SOL/USDT.
-   Configure an automated trading session.
-   Select a trading strategy.
-   Configure trading-session duration separately from strategy candle
    timeframe.
-   Define a net profit target.
-   Define a maximum acceptable loss.
-   Define the amount of capital available to the bot.
-   Restrict position size and trade frequency.
-   Execute simulated trades automatically.
-   Stop automatically when predefined boundaries are reached.
-   Monitor cryptocurrency prices and market context.
-   Review recent important crypto news.
-   Inspect portfolio and trading performance.
-   Understand why every trade was executed or rejected.
-   Eventually run the same controlled process using real funds on XT.

## 4. Operating Modes

### 4.1 Simulation Mode

Simulation is the default and first operational mode.

The user can configure virtual capital, for example 1,000 USDT. Orders
are simulated using real market information while balances, positions,
fees, and P&L are maintained internally.

Simulation should model:

-   Entry and exit prices
-   Position quantity
-   Trading fees
-   Estimated slippage
-   Realized P&L
-   Unrealized P&L
-   Portfolio balance

The same Strategy Engine, Trading Controller, and Risk Manager should
later be shared with live trading.

### 4.2 Real-Money Mode

Real-money mode is a later feature.

It will use authenticated XT APIs and should initially support only spot
trading. Futures, margin, leverage, and high-frequency trading are
outside the initial scope.

Real-money activation must be explicit and must never occur
automatically.

## 5. Trading Sessions

Trading activity is organized into explicit sessions.

Example configuration:

``` text
Mode:                Simulation
Exchange:            XT
Pair:                BTC/USDT
Capital:             500 USDT
Strategy:            EMA + RSI
Session duration:    24 hours
Signal timeframe:    5 minutes
Net profit target:   +1.0%
Maximum loss:        -0.7%
Maximum trades:      10
Maximum position:    10%
```

A session ends when its duration expires, the target profit is reached,
the maximum loss is reached, an applicable safety limit is triggered, or
the user stops it.

## 6. Session Duration vs. Signal Timeframe

These are separate concepts.

**Trading-session duration** defines how long the trading objective
applies, for example:

-   1 hour
-   4 hours
-   12 hours
-   Daily
-   Weekly
-   Custom

**Signal timeframe** defines the candle interval used by the strategy,
for example:

-   1 minute
-   5 minutes
-   15 minutes
-   1 hour
-   4 hours

A daily session can therefore execute multiple trades based on 5-minute
candles.

## 7. Trading Controller

The Trading Controller is the highest-priority functional component.

For every strategy signal it determines whether execution is permitted.

It evaluates conditions such as:

-   Is the session active?
-   Has the target profit been reached?
-   Has the loss limit been reached?
-   Has the maximum number of trades been reached?
-   Is sufficient balance available?
-   Would the trade exceed position limits?
-   Is a cooldown active?
-   Is market data current and valid?
-   Is the execution service healthy?
-   Is the emergency stop active?

Only approved signals proceed to execution.

## 8. Risk Management

Early mandatory controls:

-   Session net-profit target
-   Session maximum-loss limit
-   Maximum number of trades
-   Maximum position size
-   Capital-allocation limit
-   Emergency stop

Later controls may include:

-   Per-position stop-loss
-   Per-position take-profit
-   Trailing stop
-   Consecutive-loss limit
-   Cooldown after losses
-   Maximum daily drawdown
-   Maximum total portfolio exposure

Risk rules always take precedence over strategy signals.

## 9. Profit and Cost Calculation

The system distinguishes between gross and net performance.

``` text
Gross P&L
- Trading fees
- Slippage
- Other applicable execution costs
= Net P&L
```

Session profit targets should be evaluated using net P&L whenever
sufficient execution information is available.

This is essential because very small take-profit targets can otherwise
be consumed by trading costs.

## 10. Initial Strategy Engine

The first release should use understandable and testable conventional
strategies rather than depend on AI.

Candidate strategies include:

1.  EMA crossover with RSI filter
2.  MACD with RSI
3.  Bollinger Bands with RSI
4.  Breakout strategy

The first simulated trading vertical slice should implement only one
baseline strategy.

All strategies should implement a common interface so additional
strategies can be added without modifying execution or risk-management
logic.

## 11. Future Intelligent Trading

Future research may introduce market-regime detection such as:

-   Uptrend
-   Downtrend
-   Sideways market
-   High volatility
-   Low volatility

Later experimental capabilities may include:

-   Machine-learning prediction
-   News sentiment
-   Fear & Greed information
-   Strategy ensembles
-   Adaptive parameters
-   Reinforcement learning

AI-generated signals must obey exactly the same Trading Controller and
Risk Manager as conventional strategies.

## 12. User Interface

The application contains three principal responsive pages.

### Page 1 --- Dashboard

Purpose: quickly understand the current crypto environment.

Potential components:

-   Selected cryptocurrency prices
-   24-hour changes
-   Volume
-   Simple price chart
-   Volatility information
-   Fear & Greed indicator
-   Important recent crypto news
-   Active trading-session status
-   Current session P&L

The dashboard should remain simple rather than imitate a professional
trading terminal.

### Page 2 --- Auto Trading

This is the central application page.

Configuration includes:

-   Simulation / Real Money mode
-   XT exchange
-   Trading pair
-   Strategy
-   Session duration
-   Signal timeframe
-   Trading capital
-   Profit target
-   Maximum loss
-   Maximum number of trades
-   Position-size limit

Controls include:

-   Start Trading
-   Stop Trading
-   Emergency Stop

Monitoring includes:

-   Session status
-   Elapsed time
-   Number of trades
-   Wins and losses
-   Gross P&L
-   Fees
-   Net P&L
-   Progress toward session target
-   Current position
-   Latest decision and its reason

### Page 3 --- Portfolio

The Portfolio page includes:

-   Available balance
-   Cryptocurrency holdings
-   Portfolio value
-   Open positions
-   Unrealized P&L
-   Realized P&L
-   Session history
-   Trade history
-   Daily, weekly, and monthly performance
-   Strategy-level results where useful

Simulation and live portfolios must be clearly distinguishable.

## 13. Decision and Trade Journaling

Every material strategy decision should create a Decision Record.

Example:

``` text
Time:       13:42
Pair:       BTC/USDT
Strategy:   EMA-RSI
Signal:     BUY
Decision:   REJECTED
Reason:     Session maximum trades reached
```

Actual execution additionally creates a Trade Record containing price,
quantity, fees, timestamps, strategy, mode, and resulting P&L.

The system should make it possible to reconstruct why a trading action
did or did not occur.

## 14. Technical Architecture

### Frontend

**React**

Responsibilities:

-   Responsive user interface
-   Charts
-   Session configuration
-   Portfolio visualization
-   Trading monitoring

### Backend

**Python + FastAPI**

Responsibilities:

-   Application API
-   Market data
-   Strategy execution
-   Trading Controller
-   Risk management
-   Simulation
-   XT connectivity
-   Portfolio calculations
-   Persistence
-   Reporting
-   News integration

### Database

Initial:

**SQLite**

Future server deployment:

**PostgreSQL**

A persistence abstraction such as SQLAlchemy should minimize coupling to
a particular SQL database.

### Exchange Integration

XT is the first exchange implementation.

Core trading logic must not directly depend on XT-specific code.

Conceptual exchange boundary:

``` text
ExchangeAdapter
    get_market_data()
    get_balance()
    get_open_orders()
    create_order()
    cancel_order()
    get_order_status()
```

Initial implementation:

``` text
XTExchangeAdapter
```

## 15. Proposed Repository Structure

``` text
mycrypto/
├── backend/
│   ├── api/
│   ├── market/
│   ├── strategies/
│   ├── trading/
│   ├── risk/
│   ├── execution/
│   ├── exchanges/
│   ├── portfolio/
│   ├── simulation/
│   ├── backtesting/
│   ├── reporting/
│   ├── news/
│   ├── models/
│   └── repositories/
├── frontend/
│   ├── dashboard/
│   ├── trading/
│   ├── portfolio/
│   └── shared/
├── specs/
└── tests/
```

The exact physical structure should be finalized during Spec Kit
planning rather than treated as an immutable design.

## 16. Security

### Local Phase

Initial authentication:

-   Username/password

Exchange/API secrets:

-   Backend only
-   Never committed to Git
-   Never exposed in frontend code
-   Stored through environment or secret configuration

### Server Phase

Future capabilities:

-   Google authentication
-   HTTPS
-   Secure sessions
-   Protected endpoints
-   Production secret management
-   Access logging
-   Appropriate rate limiting

XT credentials used by the application should have only the minimum
permissions required for trading. Withdrawal capability is outside the
application's scope.

## 17. Responsive Design

Responsive behavior is required from the first frontend implementation.

The same web application should work on desktop and phone screens.

Important mobile actions include:

-   View bot status
-   Inspect P&L
-   Start simulation
-   Stop a session
-   Activate emergency stop
-   Inspect latest decisions
-   Inspect portfolio

A native Android or iOS application is not required initially.

## 18. Testing

Trading-critical logic requires automated tests.

### Unit Tests

Particularly for:

-   Strategies
-   Risk calculations
-   P&L calculations
-   Position sizing
-   Session termination
-   State transitions
-   Simulation execution

### Integration Tests

For:

-   Database behavior
-   XT market-data integration
-   Backend component integration
-   Future XT authenticated operations

### End-to-End Tests

For critical UI workflows.

Real-money execution requires additional acceptance criteria before
activation.

## 19. Development Roadmap

### Phase 0 --- Foundation

Goal: establish the Spec Kit project and software foundation.

Deliverables:

-   Project constitution
-   Repository structure
-   Python/FastAPI backend skeleton
-   React frontend skeleton
-   SQLite foundation
-   Responsive three-page navigation
-   Automated test foundation
-   Backend health endpoint

No trading and no XT integration.

### Phase 1 --- XT Market Data

Goal: obtain reliable XT public market information.

Deliverables:

-   XT adapter
-   Supported trading pairs
-   Current prices
-   Candlestick data
-   Market-data models
-   WebSocket updates where justified

No order execution.

### Phase 2 --- Simulation Trading Core

Goal: create the first complete automated-trading vertical slice.

Deliverables:

-   Simulated account
-   One trading pair
-   One strategy
-   Signal generation
-   Trading Controller
-   Risk Manager
-   Simulated execution
-   Profit target
-   Loss limit
-   Maximum trades
-   Position-size control
-   Trade journal
-   Decision journal
-   Session termination

This is the first major product milestone.

### Phase 3 --- Auto-Trading UI

Goal: control simulation through the responsive application.

Deliverables:

-   Auto Trading page
-   Session configuration
-   Start/stop controls
-   Emergency stop
-   Real-time monitoring
-   P&L
-   Latest decision/reason

### Phase 4 --- Portfolio

Goal: make performance understandable.

Deliverables:

-   Simulated wallet
-   Holdings
-   P&L
-   Trade history
-   Session history
-   Performance summaries

### Phase 5 --- Dashboard

Goal: provide useful market context.

Deliverables:

-   Crypto overview
-   Price charts
-   Market statistics
-   Recent news
-   Fear & Greed or other sentiment context where appropriate

### Phase 6 --- Backtesting

Goal: evaluate strategies before using real capital.

Deliverables:

-   Historical market data
-   Backtest runner
-   Fee/slippage assumptions
-   Net return
-   Drawdown
-   Win rate
-   Profit factor
-   Trade statistics
-   Strategy comparisons

### Phase 7 --- Strategy Laboratory

Goal: compare multiple conventional strategies.

Candidate implementations:

-   EMA + RSI
-   MACD + RSI
-   Bollinger Bands + RSI
-   Breakout

### Phase 8 --- Live XT Readiness

Goal: prepare live trading without automatically activating it.

Deliverables:

-   XT authentication
-   Account balances
-   Live-order validation
-   Connectivity handling
-   Order-state reconciliation
-   Safety checks
-   Explicit simulation/live separation

### Phase 9 --- Controlled Real-Money Trading

Goal: allow tightly controlled real-money experiments.

Initial restrictions should include:

-   Spot trading only
-   Small dedicated capital
-   One pair
-   One strategy
-   Strict session loss limit
-   Strict position limit
-   Emergency stop
-   Complete journaling

### Phase 10 --- Intelligent Trading Research

Only after sufficient evidence exists:

-   Market-regime detection
-   News/sentiment analysis
-   ML strategies
-   Adaptive strategies
-   Strategy ensembles
-   Optimization

## 20. First MVP Definition

The first meaningful MVP is **not** the complete three-page product.

It is:

> One automated simulated XT trading session executed end-to-end under
> explicit risk controls.

Example acceptance scenario:

``` text
Simulation balance:   1,000 USDT
Pair:                 BTC/USDT
Strategy:             baseline strategy
Session:              24 hours
Signal timeframe:     5 minutes
Capital allocation:   200 USDT
Net profit target:    +1.0%
Maximum loss:         -0.7%
Maximum trades:       10
```

When the session starts:

1.  XT market data is received.
2.  The strategy generates signals.
3.  Every signal passes through the Trading Controller.
4.  Risk rules approve or reject the signal.
5.  Approved trades execute against the simulated account.
6.  Rejected trades record their reason.
7.  Trading costs are incorporated.
8.  Portfolio state changes.
9.  Net P&L is continuously calculated.
10. Trading stops when a termination criterion is reached.
11. The complete decision and trade history remains inspectable.

When this works reliably, MyCrypto has its first real product.

## 21. Long-Term Evaluation Questions

The project should eventually answer these questions using recorded
evidence:

-   Does automated discipline improve consistency relative to
    discretionary intervention?
-   Which strategies remain profitable after realistic trading costs?
-   Which strategies work in which market regimes?
-   How sensitive are results to session profit targets?
-   Does a very small take-profit improve consistency or primarily
    increase fee exposure?
-   What trade frequency provides the best risk-adjusted result?
-   How large are realistic drawdowns?
-   Does sentiment information add measurable value?
-   Can regime-aware strategy selection improve performance?

## 22. Spec-Driven Development Strategy

MyCrypto will be developed as independent, verifiable features.

Planned feature sequence:

``` text
000 Constitution
001 Project Foundation
002 XT Market Data
003 Simulation Trading Core
004 Auto-Trading UI
005 Portfolio
006 Dashboard
007 Backtesting
008 Multiple Strategies
009 Live XT Integration
```

Each substantial feature should follow the Spec Kit workflow:

``` text
Constitution
    ↓
Specify
    ↓
Clarify
    ↓
Plan
    ↓
Checklist
    ↓
Tasks
    ↓
Analyze
    ↓
Implement
    ↓
Verify / Converge
```

Specifications define intended behavior before implementation.
Implementation details belong primarily in planning. Each completed
feature should leave the project runnable and testable.

## 23. Immediate Development Target

The first feature to implement is:

**001 --- Project Foundation**

Scope:

-   Python/FastAPI backend
-   React frontend
-   SQLite foundation
-   Responsive application shell
-   Dashboard route
-   Auto Trading route
-   Portfolio route
-   Backend health endpoint
-   Basic test infrastructure

Explicitly excluded:

-   XT integration
-   Trading algorithms
-   Simulated trading
-   Real-money trading
-   News
-   AI/ML
-   Backtesting

The purpose of Feature 001 is to establish a small, understandable
vertical foundation and validate the Spec Kit workflow before
implementing trading-critical functionality.
