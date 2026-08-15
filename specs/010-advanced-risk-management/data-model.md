# Data Model: Advanced Risk Management

**Feature**: `010-advanced-risk-management`  
**Date**: 2026-08-14  
**Related**: Feature 003 sessions; Feature 008 defaults; Feature 009 portfolio

## Entities

### Shared Risk Catalog Entry

Not a DB table — code module constants.

| Field | Notes |
|-------|--------|
| `code` | Stable string id (machine) |
| `message` | Default human-readable text |
| `layer` | `controller` \| `risk` \| `execution` \| `stop` \| `validation` |

Existing 003/004 codes retained. New codes (additive):

| Code | Typical use |
|------|-------------|
| `insufficient_portfolio_available` | Create/start: allocated > available |
| `allocation_exposure_exceeded` | BUY would exceed bound reserved |
| `allocation_release_blocked` | Release while session bound |
| `allocation_resize_blocked` | Resize below deployed while bound |
| `portfolio_max_loss` | Stop: loss ≥ bound |
| `portfolio_max_loss_uncomputable` | BUY blocked; metric kind not computable |
| `per_symbol_exposure_exceeded` | Projected weight > cap |

### Effective Simulation Risk Configuration

Persisted on `simulation_sessions` at create/start (copy from request /
Settings). Immutable for that session after start (Settings changes ignored).

| Field | Type / notes | Required |
|-------|----------------|----------|
| Existing session risk fields | allocated, max position, profit/loss rates+amounts, max trades, duration, fees | yes (003) |
| `allocationId` | FK-like id of Feature 009 allocation, or null | no |
| `portfolioMaxLossRate` | Fraction of baseline, or null | no |
| `portfolioMaxLossAmount` | Derived and/or absolute USDT string, or null | no* |
| `portfolioLossBaselineKind` | `equity` \| `quote_cash` | yes if max-loss configured; set at start |
| `portfolioLossBaselineValue` | Decimal string | yes if max-loss configured; set at start |
| `perSymbolMaxWeight` | Ratio string (e.g. `"0.40"`), or null | no |

\* If only a rate is supplied, derive amount from baseline at start and persist
both. If only an amount is supplied, persist amount (rate may be null).

### Portfolio Risk Baseline

Logical subset of the session row: kind + value frozen at start when portfolio
max-loss is configured. Never recomputed when completeness changes.

### Allocation Binding

| Field | Notes |
|-------|--------|
| Session `allocationId` | Optional; at most one |
| Deployed for binding | Session open long `cost_basis` USDT when long; else `"0"` |
| Remaining | `allocation.reservedSize − deployed` |

### Risk Decision (runtime)

| Field | Notes |
|-------|--------|
| `approved` | bool |
| `reasonCode` | First failing code or null |
| `reasonMessage` | Catalog message or null |
| `triggerStop` | Stop reason code when hard stop should fire (e.g. `portfolio_max_loss`, `max_trades`) |

### Settings defaults extensions (Feature 008)

Optional fields on operator defaults for **new** Simulation forms only:

| Field | Notes |
|-------|--------|
| `portfolioMaxLossRate` / `portfolioMaxLossAmount` | Optional |
| `perSymbolMaxWeight` | Optional |
| `preferredAllocationId` | Optional prefill only; not a live FK |

## Relationships

```text
Simulation Session (1)
  ├── optional Allocation Binding → Portfolio Allocation (0..1)
  ├── Portfolio Risk Baseline (0..1)   # when max-loss configured
  └── Decision / Stop journals (reason_code + reason_message)

RiskManager (shared)
  ├── Simulation pipeline (portfolio context ON)
  └── Backtest / Comparison (portfolio context OFF)
```

## Validation rules

1. Create/start: `allocated_capital ≤ portfolio.available` (else
   `insufficient_portfolio_available`).
2. Bound BUY: intended notional ≤ allocation remaining.
3. Release bound allocation: reject (`allocation_release_blocked`).
4. Resize bound allocation: `newReserved ≥ deployed` else
   `allocation_resize_blocked`.
5. Max-loss: evaluate only under frozen kind; uncomputable → BUY reject
   (`portfolio_max_loss_uncomputable`); reached → stop (`portfolio_max_loss`).
6. Per-symbol: projected post-BUY weight; fail closed if incomplete; USDT
   excluded.
7. Precedence: first failing reason only (see contracts/risk-catalog.md).
8. Settings changes never mutate persisted session risk fields.

## State transitions (portfolio max-loss)

```text
[start] ──persist baseline──► [armed]
[armed] ──loss ≥ bound (computable)──► stop(portfolio_max_loss)
[armed] ──metric uncomputable──► reject BUYs (session may continue)
[armed] ──metric computable again──► resume loss evaluation
```
