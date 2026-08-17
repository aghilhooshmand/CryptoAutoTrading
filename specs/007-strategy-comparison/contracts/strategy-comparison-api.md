# Contract: Strategy Comparison API

**Feature**: `007-strategy-comparison`  
**Date**: 2026-08-12  
**Consumer**: Auto Trading frontend  
**Depends on**: Feature 004 `/backtest` inspect endpoints; Feature 005/006
`GET /strategies`

Local/unauthenticated. Synchronous create. No WebSockets.

---

## `POST /comparisons`

Create and run a comparison. Returns only when status is `completed` or
`failed` (or `400`/`409` pre-accept / conflict errors with **no** durable
comparison row for validation/oversized rejects).

**Success / post-accept failure:** HTTP **`201`** with comparison body
(`status: "completed"` or `status: "failed"`).

### Request body

Shared fields align with Feature 004 backtest create (pair, timeframe,
start/end, capital nesting, fee/slippage, optional common risk limits).

```json
{
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": 1700000000000,
  "endTime": 1700100000000,
  "startingCapital": "1000",
  "allocatedCapital": "1000",
  "maxPositionSize": "1000",
  "feeRate": "0.001",
  "slippageRate": "0.0005",
  "maxTrades": null,
  "legs": [
    { "strategyId": "dual_ema", "strategyParams": { "fastPeriod": 9, "slowPeriod": 21 } },
    { "strategyId": "rsi", "strategyParams": { "period": 14, "overbought": 70, "oversold": 30 } }
  ]
}
```

| Rule | Error |
|------|--------|
| `legs.length < 2` or `> 5` | `400` `invalid_comparison` |
| Unknown strategy / bad params | `400` (`unknown_strategy` / `invalid_strategy_params`) |
| Capital nesting / window invalid | `400` `invalid_config` |
| Oversized history estimate | `400` `oversized_history` (no row) |
| Another comparison (or conflicting run lock) in flight | `409` as documented |

### Amendment 2026-08-17 — Product identity (C1)

Create and read MUST support `venue`, `baseAsset`, `quoteAsset`,
`canonicalSymbol`, `venueProductId` on the comparison (shared across legs).
`symbol` is a compatibility alias. New Kraken-default comparisons MUST persist
and return identity fields. Omit `venue` + XT-form `symbol` ⇒ `venue=xt`. Do
not rewrite historical comparison rows. Shared candles MUST come from the
persisted venue only.

### Success response (`201`)

```json
{
  "id": "…",
  "status": "completed",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": 1700000000000,
  "endTime": 1700100000000,
  "candleCount": 120,
  "buyAndHoldReturnPct": "0.05",
  "buyAndHoldNetPnl": "50",
  "legs": [
    {
      "ordinal": 0,
      "strategyId": "dual_ema",
      "strategyParams": { "fastPeriod": 9, "slowPeriod": 21 },
      "backtestRunId": "…",
      "netPnl": "…",
      "returnPct": "…",
      "maxDrawdown": "…",
      "maxDrawdownPct": "…",
      "winRate": "…",
      "roundTripCount": 3,
      "fillCount": 7,
      "totalFees": "…",
      "totalSlippage": "…",
      "bestTrade": "…",
      "worstTrade": "…",
      "buyAndHoldReturnPct": "0.05",
      "vsBuyAndHoldReturnPct": "…"
    }
  ]
}
```

Notes:
- `fillCount` is the comparison-facing name for engine `strategyFillCount`.
- No `bestStrategyId`, `winner`, or equivalent field.
- **HTTP status (aligned with Feature 004 backtest create):**
  - Pre-accept validation / oversized estimate → `400` with error body; **no** comparison row.
  - After accept: always `201` with a durable comparison body whose `status` is `completed` or `failed`.
  - Failed body MUST include `errorCode` / `errorMessage` and MUST NOT invent a partial metrics leaderboard.
  - Another comparison already in flight → `409` (documented conflict).

Wire `comparisonId` (JSON) ↔ `comparison_id` (persistence) explicitly in serializers.

---

## `GET /comparisons`

List recent comparisons (respect retention). Default limit suitable for local
UI (e.g. 10–20).

## `GET /comparisons/{id}`

Full comparison including leg metrics and `backtestRunId` links.

## `DELETE /comparisons/{id}`

Delete comparison record. MUST NOT be required to cascade-delete leg
backtests (legs remain under Feature 004 retention unless product later
defines explicit cascade — default: **no cascade delete of legs**).

---

## Backtest history filter (Feature 004 extension)

### `GET /backtest/runs`

Add query control, e.g.:

| Param | Behavior |
|-------|----------|
| (default) | Exclude `origin=comparison` |
| `includeComparisonOrigin=true` | Include comparison-originated runs |

Each run payload SHOULD expose `origin` (`manual` \| `comparison`) and optional
`comparisonId` so the UI can badge/filter.

### Inspect (unchanged)

`GET /backtest/runs/{id}`, `/trades`, `/decisions` work for comparison legs
when the run still exists.

---

## Frontend expectations

- Auto Trading hosts comparison config + results (no new primary nav).
- Multi-leg editor: 2–5 legs, each with strategy selector + dynamic params.
- Results table shows all FR-006 metrics; **no** automatic best/winner chrome.
- Default backtest history hides comparison-originated runs; comparison
  results link to leg inspect.
- Optional column sort by the operator is allowed; must not label a winner.
