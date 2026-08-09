# Contract: Simulation Trading API

**Feature**: `003-simulation-trading-core`  
**Date**: 2026-08-09  
**Consumer**: Auto Trading frontend and automated tests

All endpoints are local/unauthenticated (single-operator). Responses use
**decimal strings** for money and rates. No XT field names or private trading
payloads.

Base path: `/simulation`  
Content-Type: `application/json`

### Defaults

When omitted on create:

| Field | Default |
|-------|---------|
| `feeRate` | `"0.001"` (0.10%) |
| `slippageRate` | `"0.0005"` (0.05%) |
| `strategyId` | `"dual_ema_9_21"` |
| `mode` | `"simulation"` |

`mode: "real_money"` MUST be rejected at create/start with
`real_money_unavailable`. Feature 003 does not implement real XT execution.

### `maxTrades`

Limits **strategy-driven** fills only. After `strategyFillCount` reaches
`maxTrades`, no further strategy execution is allowed. If the session is LONG,
one forced safety close is still allowed and may make `tradeCount` equal
`maxTrades + 1`; that trade MUST have `isForcedClose: true`.

---

## `POST /simulation/sessions`

Create a session in `CONFIGURED`.

### Request body

```json
{
  "mode": "simulation",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startingCapital": "10000",
  "allocatedCapital": "10000",
  "maxPositionSize": "10000",
  "targetNetProfit": "100",
  "maxSessionLoss": "200",
  "maxTrades": 20,
  "durationSeconds": 3600,
  "feeRate": "0.001",
  "slippageRate": "0.0005"
}
```

`allocatedCapital` MAY be omitted; server sets it equal to `startingCapital`.

### Success

- HTTP `201` — session body (see Session resource)

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Validation failure | `400` | `invalid_config` |
| `real_money` mode | `400` | `real_money_unavailable` |
| Unsupported symbol (if checked at create) | `400` | `unsupported_symbol` |

---

## `POST /simulation/sessions/{id}/start`

Transition `CONFIGURED` → `RUNNING` if allowed.

### Success

- HTTP `200` — updated session

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `session_not_found` |
| Wrong state | `409` | `invalid_state` |
| Another session active | `409` | `session_already_active` |
| Market data unavailable for symbol | `503` | `market_data_unavailable` |

---

## `POST /simulation/sessions/{id}/stop`

Manual stop: `RUNNING` → `STOPPING` → `STOPPED` (forced close if safe price).

### Success

- HTTP `200` — updated session (`stopReason: "manual"`)

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `session_not_found` |
| Not running | `409` | `invalid_state` |

---

## `POST /simulation/sessions/{id}/emergency-stop`

Emergency stop: same state path; `stopReason: "emergency"`. Halts new
strategy-driven execution immediately.

### Success

- HTTP `200` — updated session

---

## `GET /simulation/sessions/active`

Returns the `RUNNING` or `STOPPING` session if any, else `null` body field.

### Success

```json
{
  "session": null
}
```

or `{ "session": { ... } }`

---

## `GET /simulation/sessions/{id}`

Full session resource + embedded economics snapshot when computable.

### Session resource (illustrative)

```json
{
  "id": "11111111-1111-1111-1111-111111111111",
  "mode": "simulation",
  "state": "RUNNING",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "strategyId": "dual_ema_9_21",
  "startingCapital": "10000",
  "allocatedCapital": "10000",
  "maxPositionSize": "10000",
  "targetNetProfit": "100",
  "maxSessionLoss": "200",
  "maxTrades": 20,
  "durationSeconds": 3600,
  "feeRate": "0.001",
  "slippageRate": "0.0005",
  "cash": "10000",
  "positionSide": "flat",
  "positionQty": "0",
  "tradeCount": 0,
  "strategyFillCount": 0,
  "startedAt": "2026-08-09T17:00:00.000Z",
  "stoppedAt": null,
  "stopReason": null,
  "positionFlattenStatus": "n/a",
  "lastProcessedCandleOpenTime": null,
  "economics": {
    "startEquity": "10000",
    "cash": "10000",
    "markEquity": "10000",
    "markNetPnl": "0",
    "unrealizedGross": "0",
    "liquidationEquity": "10000",
    "grossPnl": "0",
    "fees": "0",
    "slippageCost": "0",
    "netPnl": "0",
    "markPrice": "65000.00",
    "markSafe": true
  },
  "label": "SIMULATION"
}
```

`economics.netPnl` is the **hard-limit** Session NET (`liquidationEquity -
startEquity`). `markEquity` / `markNetPnl` / `unrealizedGross` are
informational. When mark unsafe while long: `netPnl`, `liquidationEquity`, and
mark fields that require a price MAY be `null` with `markSafe: false`.

Hypothetical liquidation costs used to evaluate profit/loss stops are not
separate ledger entries; an actual forced close applies fee/slippage once.
---

## `GET /simulation/sessions/{id}/decisions`

### Query

| Param | Notes |
|-------|--------|
| `limit` | Optional, default 100, max 500 |

### Success

```json
{
  "items": [
    {
      "id": "...",
      "createdAt": "2026-08-09T17:05:00.000Z",
      "candleOpenTime": 1723204800000,
      "signal": "HOLD",
      "outcome": "hold",
      "reasonCode": null,
      "reasonMessage": null,
      "fastEma": "64910.12",
      "slowEma": "64880.01"
    }
  ]
}
```

---

## `GET /simulation/sessions/{id}/trades`

Same pagination idea as decisions.

### Success item fields

`id`, `createdAt`, `symbol`, `side`, `qty`, `referencePrice`, `fillPrice`,
`fee`, `slippageCost`, `notional`, `cashDelta`, `isForcedClose`,
`candleOpenTime`.

---

## Error body shape

```json
{
  "error": {
    "code": "invalid_config",
    "message": "maxTrades must be >= 1"
  }
}
```

---

## Acceptance mapping

| Spec | Behavior |
|------|----------|
| FR-001, FR-020 | `mode` simulation; `label: SIMULATION`; real money rejected |
| FR-004 | `session_already_active` on second start |
| FR-010–011 | decisions + trades endpoints |
| FR-012a | fee/slippage defaults |
| FR-014 | `netPnl` / limits use liquidation equity while LONG |
| FR-015–016 | stop / emergency-stop; no new exec when stopped |
| FR-015a | forced close reflected in trades + flatten status; `isForcedClose` |
| SC-007 | no private XT trading routes; real_money rejected at API |
