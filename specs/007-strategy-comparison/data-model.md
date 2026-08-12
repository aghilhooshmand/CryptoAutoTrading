# Data Model: Strategy Comparison and Evaluation

**Feature**: `007-strategy-comparison`  
**Date**: 2026-08-12  
**Related**: Feature 004 `BacktestRun` / trades / decisions; Feature 005/006 strategy registry

## Entities

### StrategyComparison

| Field | Description |
|-------|-------------|
| `id` | Stable identifier |
| `status` | `running` \| `completed` \| `failed` |
| `symbol` | Trading pair (shared) |
| `timeframe` | Shared signal timeframe |
| `startTime` / `endTime` | Historical window (ms) |
| `startingCapital`, `allocatedCapital`, `maxPositionSize` | Shared nesting |
| `feeRate`, `slippageRate` | Shared costs |
| Optional common risk | Same optional Feature 004 fields (e.g. `maxTrades`, profit/loss rates) when set |
| `candleCount` | Shared fetched closed-candle count |
| `buyAndHoldReturnPct` | Shared B&H return for the window |
| `buyAndHoldNetPnl` | Shared B&H net P&L (optional but recommended) |
| `errorCode` / `errorMessage` | When `failed` |
| `createdAt` / `completedAt` | Timestamps |
| `legs` | Ordered list of ComparisonLeg (2–5) |

**Retention**: FIFO keep latest **10** `completed` and **5** `failed` comparisons.

**Validation**:
- Capital nesting: `0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital`
- `2 ≤ len(legs) ≤ 5`
- Each leg: known strategy id + valid params
- Pre-accept oversized window reject (no comparison row)
- After fetch: `candleCount ≥ max(leg.min_history_candles)` else fail /
  `insufficient_history`

### ComparisonLeg

| Field | Description |
|-------|-------------|
| `id` | Leg identifier within comparison |
| `ordinal` | Display/run order (0-based or 1-based; stable) |
| `strategyId` | Canonical registry id |
| `strategyParams` | Effective params JSON for this leg |
| `backtestRunId` | FK/link to `BacktestRun` (nullable if failed before persist) |
| Summary metrics | See below (required when comparison `completed`) |

**Summary metrics (required on completed legs)**:

| Field | Source |
|-------|--------|
| `netPnl` | Engine |
| `returnPct` | Engine |
| `maxDrawdown` | Engine |
| `maxDrawdownPct` | Engine (include for parity with Feature 004 UI) |
| `winRate` | Engine |
| `roundTripCount` | Engine |
| `fillCount` | Alias of engine `strategyFillCount` |
| `totalFees` | Engine |
| `totalSlippage` | Engine |
| `bestTrade` | Engine |
| `worstTrade` | Engine |
| `buyAndHoldReturnPct` | Shared comparison B&H |
| `vsBuyAndHoldReturnPct` | `returnPct − buyAndHoldReturnPct` |

Same `strategyId` MAY appear on multiple legs with different `strategyParams`.

### BacktestRun (extension)

Existing Feature 004 run, plus:

| Field | Description |
|-------|-------------|
| `origin` | `manual` (default) \| `comparison` |
| `comparisonId` | Optional link to StrategyComparison when `origin=comparison` |

Comparison-created runs set `origin=comparison`. Default history list excludes
them unless the operator includes them.

### SharedMarketWindow (logical)

Not necessarily a separate table — represented by comparison header fields +
in-memory candle series during the sync run. All legs MUST use that same series.

### BuyAndHoldBenchmark (logical)

Computed once per comparison for the shared window and cost assumptions;
stored on the comparison (and mirrored onto each leg row’s B&H fields).

## Relationships

```text
StrategyComparison 1──* ComparisonLeg
ComparisonLeg 0..1──1 BacktestRun   (when leg persisted)
BacktestRun.comparisonId → StrategyComparison (when origin=comparison)
```

## State transitions

### StrategyComparison

```text
(no row) --pre-accept validation fail--> (no row)
(no row) --accept--> running
running --all legs ok--> completed
running --any leg/orchestrator fail--> failed
```

No `completed` with mixed failed legs.

### BacktestRun (leg)

Same Feature 004 transitions (`running` → `completed` | `failed`), created
under comparison ownership during the sync orchestrator.

## Non-goals (data)

- No optimization trial tables
- No ranking / winner flags on comparisons or legs
- No real-money order entities
