# Contract: Backtest API

**Feature**: `004-backtesting-core`  
**Date**: 2026-08-11  
**Consumer**: Auto Trading frontend and automated tests

All endpoints are local/unauthenticated (single-operator). Responses use
**decimal strings** for money and rates. No XT field names or private trading
payloads. No WebSockets.

Base path: `/backtest`  
Content-Type: `application/json`

Error envelope matches Feature 002/003:

```json
{
  "error": {
    "code": "invalid_config",
    "message": "Human-readable reason",
    "details": {}
  }
}
```

---

## Defaults

When omitted on create/run:

| Field | Default |
|-------|---------|
| `feeRate` | `"0.001"` (0.10%) |
| `slippageRate` | `"0.0005"` (0.05%) |
| `strategyId` | `"dual_ema_9_21"` (fixed; other values rejected) |
| `maxTrades` | omitted → **no** strategy-fill cap |
| `targetNetProfitRate` | omitted → no profit early exit |
| `maxSessionLossRate` | omitted → no loss early exit |

### Capital nesting

```text
0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital
```

Violations → HTTP `400` / `invalid_config`.

### History limits

`MAX_BACKTEST_CANDLES = 5000` (see [research.md](../research.md) Decision 4).

Oversized window (estimate or fetch) → HTTP `400` / `oversized_history`.
Never silently truncate.

### Fill semantics (operator-visible)

- Strategy signal on closed Candle **N**; if Controller + Risk approve,
  HistoricalExecutionAdapter fills at Candle **N+1 open** + fee/slippage.
- No N+1 → no fill; decision `outcome: "approved_unexecutable"`,
  `reasonCode: "no_next_candle"` — **not** `rejected`.
- `rejected` is reserved for controller/risk denial only.
- End-of-run flatten (if still long): final processed closed candle **close** +
  fee/slippage; `isEndOfRunFlatten: true`.

### Retention

- Max **20** completed runs (FIFO oldest `completedAt`).
- Max **5** failed runs (FIFO oldest failure timestamp); separate quota.
- Sync execution under 5000-candle cap (v1).

### Concurrency

At most one `running` backtest. Concurrent start → HTTP `409` /
`backtest_already_running`.

### Isolation

Backtest MUST NOT mutate live simulation session state. Running a backtest
while a simulation session is active is allowed.

---

## `POST /backtest/runs`

Validate config, reject oversized history, execute Dual EMA backtest
**synchronously** (v1, ≤5000 candles), persist result (FIFO 20 completed /
FIFO 5 failed), return completed (or failed) run with summary.

### Request body

```json
{
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": 1719792000000,
  "endTime": 1722470400000,
  "startingCapital": "1000",
  "allocatedCapital": "1000",
  "maxPositionSize": "1000",
  "targetNetProfitRate": "0.01",
  "maxSessionLossRate": "0.007",
  "maxTrades": 50,
  "feeRate": "0.001",
  "slippageRate": "0.0005"
}
```

Optional fields may be omitted: `targetNetProfitRate`, `maxSessionLossRate`,
`maxTrades`, `feeRate`, `slippageRate`.

When profit/loss rates are provided, server derives and returns absolute
amounts (same relationship as Feature 003).

### Success

- HTTP `201` — run resource with `status: "completed"` and `summary` populated  
  (or `status: "failed"` with error fields if market/history failed after
  accept — prefer failing before persist when validation fails with `400`)

Preferred: validation and history-size checks fail with `400` **before**
creating a durable run. Runtime market failures after start may yield
`failed` row or `503` without durable row — implementers SHOULD prefer clear
`400`/`503` without counting toward the 20 completed retention.

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Validation / capital nesting / bad window | `400` | `invalid_config` |
| Window exceeds max candles | `400` | `oversized_history` |
| Insufficient / empty history | `400` or `503` | `insufficient_history` |
| Unsupported symbol / timeframe | `400` | `unsupported_symbol` / `unsupported_timeframe` |
| Another backtest running | `409` | `backtest_already_running` |
| Market data unavailable | `503` | `market_data_unavailable` |

---

## `GET /backtest/runs`

List stored runs (newest first). Includes completed and recent failed.

### Query

| Param | Notes |
|-------|--------|
| `limit` | Optional; default 20; max 50 |

### Success

- HTTP `200`

```json
{
  "runs": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "status": "completed",
      "symbol": "btc_usdt",
      "timeframe": "1h",
      "startTime": 1719792000000,
      "endTime": 1722470400000,
      "createdAt": "2026-08-11T12:00:00Z",
      "completedAt": "2026-08-11T12:00:05Z",
      "summary": {
        "netPnl": "12.34",
        "returnPct": "0.01234",
        "tradeCount": 4
      }
    }
  ]
}
```

List may return a **summary subset** of metrics; full summary on get-by-id.

---

## `GET /backtest/runs/{id}`

Full configuration + summary for one run.

### Success

- HTTP `200` — full run resource (see below)

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `run_not_found` |

---

## `GET /backtest/runs/{id}/trades`

### Success

- HTTP `200`

```json
{
  "trades": [
    {
      "id": "22222222-2222-2222-2222-222222222222",
      "side": "BUY",
      "qty": "0.01",
      "referencePrice": "60000",
      "fillPrice": "60030",
      "fee": "6.003",
      "slippageCost": "0.30",
      "notional": "600.30",
      "signalCandleOpenTime": 1719795600000,
      "fillCandleOpenTime": 1719799200000,
      "isEndOfRunFlatten": false,
      "isForcedClose": false
    }
  ]
}
```

---

## `GET /backtest/runs/{id}/decisions`

### Success

- HTTP `200`

```json
{
  "decisions": [
    {
      "id": "33333333-3333-3333-3333-333333333333",
      "candleOpenTime": 1719795600000,
      "signal": "HOLD",
      "outcome": "hold",
      "reasonCode": null,
      "reasonMessage": null,
      "fastEma": "60100.1",
      "slowEma": "59950.2"
    },
    {
      "id": "44444444-4444-4444-4444-444444444444",
      "candleOpenTime": 1722466800000,
      "signal": "BUY",
      "outcome": "approved_unexecutable",
      "reasonCode": "no_next_candle",
      "reasonMessage": "Approved by risk but no next candle open for fill",
      "fastEma": "61000.0",
      "slowEma": "60500.0"
    }
  ]
}
```

`outcome` values: `hold` | `approved` | `approved_unexecutable` | `rejected` |
`forced`. Never map `no_next_candle` to `rejected`.

---

## `DELETE /backtest/runs/{id}`

Removes run and cascaded trades/decisions.

### Success

- HTTP `204` — empty body

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `run_not_found` |
| Currently running | `409` | `invalid_state` |

---

## Run resource (full)

```json
{
  "id": "11111111-1111-1111-1111-111111111111",
  "status": "completed",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": 1719792000000,
  "endTime": 1722470400000,
  "startingCapital": "1000",
  "allocatedCapital": "1000",
  "maxPositionSize": "1000",
  "targetNetProfitRate": "0.01",
  "maxSessionLossRate": "0.007",
  "targetNetProfitAmount": "10",
  "maxSessionLossAmount": "7",
  "maxTrades": 50,
  "feeRate": "0.001",
  "slippageRate": "0.0005",
  "strategyId": "dual_ema_9_21",
  "candleCount": 720,
  "createdAt": "2026-08-11T12:00:00Z",
  "startedAt": "2026-08-11T12:00:00Z",
  "completedAt": "2026-08-11T12:00:05Z",
  "errorCode": null,
  "errorMessage": null,
  "summary": {
    "startingCapital": "1000",
    "endingCapital": "1012.34",
    "netPnl": "12.34",
    "returnPct": "0.01234",
    "tradeCount": 4,
    "roundTripCount": 2,
    "winningTrades": 1,
    "losingTrades": 1,
    "winRate": "0.5",
    "totalFees": "2.40",
    "totalSlippage": "0.60",
    "maxDrawdown": "25.00",
    "maxDrawdownPct": "0.025",
    "bestTrade": "20.00",
    "worstTrade": "-7.66",
    "buyAndHoldNetPnl": "8.00",
    "buyAndHoldReturnPct": "0.008",
    "strategyFillCount": 3
  }
}
```

JSON field names use **camelCase** at the HTTP boundary (same convention as
Feature 003 simulation API).

---

## Market-data dependency (not under `/backtest`)

Feature 002 candle retrieval MUST gain range support used only via the
normalized service/adapter:

- Inputs: `symbol`, `interval`, `startTime`, `endTime` (UTC ms)
- Output: normalized closed candles only
- Adapter may page XT `startTime`/`endTime`; XT types MUST NOT leak into
  `/backtest` responses

Document the Feature 002 extension in implementation tasks; backtest clients
do **not** call XT directly.
