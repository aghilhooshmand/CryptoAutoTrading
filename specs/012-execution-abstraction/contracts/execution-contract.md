# Contract: Shared Execution Engine (012)

**Feature**: `012-execution-abstraction`  
**Date**: 2026-08-15  
**Kind**: Internal Python protocol (not an HTTP API)

No public REST changes in Feature 012. This document is the acceptance
contract for adapters and callers.

---

## Protocol

```text
ExecutionEngine.execute(intent: ExecutionIntent) -> FillResult
```

All production **strategy-fill** paths for Historical and Simulation MUST
invoke an adapter that implements this protocol (directly or via thin
`buy`/`sell` wrappers that **MUST** call `self.execute` and MUST NOT call
shared economics helpers directly).

Compatibility shims at legacy import paths (`app.simulation.execution.*`,
`app.backtest.execution`) MUST be **re-export-only** with zero local fill
implementation bodies.

---

## ExecutionIntent (required fields)

| Field | Type (logical) | Notes |
|-------|----------------|-------|
| side | `BUY` \| `SELL` | |
| symbol | string | |
| reference_price | decimal | Caller-supplied; adapter does not fetch market data |
| fee_rate | decimal | |
| slippage_rate | decimal | |
| cash | decimal | |
| allocated_capital | decimal | |
| max_position_size | decimal | |
| position_side | `flat` \| `long` | |
| position_qty | decimal | |
| is_forced_close | bool | default false |

---

## FillResult

| Field | Success | Failure |
|-------|---------|---------|
| ok | true | false |
| reason_code | optional / null | required stable code |
| reason_message | optional | recommended |
| fill | FillQuote | null |
| qty | decimal | null |
| venue_order_id | optional / null | optional (amendment 2026-08-17) |

Keep legacy `xt_order_id` until Feature 015 Kraken writes. Simulation/Backtest
fill outcomes MUST NOT change (FR-018).

### Established failure codes (must remain stable)

| Code | Typical cause |
|------|----------------|
| `invalid_side` | side not BUY/SELL |
| `conflicting_position_state` | BUY not from flat / SELL not from long |
| `insufficient_balance` | dust, zero qty, or cash cannot cover BUY |

### New code (Real stub only)

| Code | Meaning |
|------|---------|
| `real_execution_unavailable` | Real adapter invoked; no order; no state mutation |

---

## Adapter obligations

### HistoricalExecutionAdapter

- Implements `execute`; may expose `buy`/`sell` wrappers that build intents and
  call **`self.execute` only** (never call shared economics directly).
- Uses caller `reference_price` (next-open for strategy fills; established
  flatten refs for end-of-run / hard-stop).
- MUST NOT read Portfolio or mutate Portfolio.
- MUST NOT fetch live quotes.
- Optional migration alias: `HistoricalFillResult = FillResult` (same fields).

### SimulationExecutionEngine

- Implements `execute` (runtime name; constitution “SimulationExecutionAdapter”
  is conceptual — do not rename mid-012).
- Uses caller `reference_price` from Simulation live/safe mark path.
- MUST NOT perform journal writes or Portfolio apply inside shared economics;
  callers retain those side effects after a successful fill.
- MUST NOT import Controller, Risk, journal repos, or Portfolio mutation APIs.

### RealExecutionAdapter

- Implements `execute`.
- Always returns failure with `reason_code=real_execution_unavailable`.
- MUST NOT place exchange orders, touch credentials, or mutate trading /
  accounting / Portfolio state.
- MUST NOT be exposed as an operator-selectable mode in create/run UI or
  session APIs in Feature 012.

---

## Caller obligations (mode-owned)

| Concern | Owner |
|---------|--------|
| Next-open vs live mark selection | Backtest engine / Simulation pipeline |
| `approved_unexecutable` when no next candle | Backtest engine (before execute) |
| Decision / trade journal rows | Mode pipelines |
| Forced / end-of-run flatten orchestration | Mode pipelines |
| Portfolio holdings / reserved updates | Simulation only, after successful fill |

---

## Out of contract (012)

- HTTP endpoints
- XT private order placement
- Changing Risk catalogs or Decision Log Mode
- Renaming existing Simulation/Backtest reject codes
