# Contract: Strategy Registry & Selection API

**Feature**: `005-strategy-framework`  
**Date**: 2026-08-11  
**Consumer**: Auto Trading frontend (Simulation + Backtest) and automated tests

Local/unauthenticated. Decimal strings where money/rates appear on related
APIs; strategy period parameters are **JSON integers**.

## Breaking change vs Feature 003

Feature 003 create previously defaulted `strategyId` to `"dual_ema_9_21"` when
omitted. **Feature 005 requires `strategyId` on create.** Omission → `400`.
UI MUST send `strategyId` (pre-fill `"dual_ema"`).

Legacy alias `"dual_ema_9_21"` remains **accepted** when explicitly supplied.

Fee/slippage defaults remain whatever Features 003/004 currently ship (e.g. XT
VIP0 fee); this contract does not redefine them.

---

## `GET /strategies`

List registered strategies and parameter schemas for UI rendering.

**Response** `200`:

```json
{
  "strategies": [
    {
      "id": "dual_ema",
      "displayName": "Dual EMA",
      "aliases": ["dual_ema_9_21"],
      "parameters": [
        {
          "name": "fastPeriod",
          "type": "integer",
          "label": "Fast EMA period",
          "default": 9,
          "minimum": 1
        },
        {
          "name": "slowPeriod",
          "type": "integer",
          "label": "Slow EMA period",
          "default": 21,
          "minimum": 2
        }
      ],
      "constraints": [
        {
          "code": "fast_lt_slow",
          "message": "fastPeriod must be strictly less than slowPeriod"
        }
      ]
    }
  ]
}
```

Notes:
- List contains **canonical** ids only (not a separate entry for the alias).
- With only Dual EMA registered, `strategies.length === 1`.

---

## Simulation create — strategy fields

`POST /simulation/sessions`

### Required / optional

| Field | Required | Notes |
|-------|----------|-------|
| `strategyId` | **Yes** | Canonical `dual_ema` or alias `dual_ema_9_21` |
| `strategyParams` | No | Object; omitted keys take registry defaults |

### Example body (excerpt)

```json
{
  "mode": "simulation",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startingCapital": "500",
  "allocatedCapital": "500",
  "maxPositionSize": "500",
  "targetNetProfitRate": "0.01",
  "maxSessionLossRate": "0.007",
  "maxTrades": 20,
  "durationSeconds": 3600,
  "strategyId": "dual_ema",
  "strategyParams": {
    "fastPeriod": 9,
    "slowPeriod": 21
  }
}
```

### Response session object (excerpt)

```json
{
  "id": "…",
  "strategyId": "dual_ema",
  "strategyParams": {
    "fastPeriod": 9,
    "slowPeriod": 21
  }
}
```

Even if the client sent `"strategyId": "dual_ema_9_21"`, the response
**MUST** use `"dual_ema"` and include effective `strategyParams`.

### Errors

| Condition | HTTP | `error.code` (suggested) |
|-----------|------|---------------------------|
| Missing `strategyId` | 400 | `invalid_config` or `missing_strategy` |
| Unknown id | 400 | `unknown_strategy` |
| Invalid params | 400 | `invalid_strategy_params` |

(Existing capital/mode errors unchanged.)

---

## Backtest create — strategy fields

`POST /backtest/runs`

Same strategy field rules as simulation.

### Example body (excerpt)

```json
{
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": 1700000000000,
  "endTime": 1700600000000,
  "startingCapital": "1000",
  "allocatedCapital": "1000",
  "maxPositionSize": "1000",
  "strategyId": "dual_ema",
  "strategyParams": {
    "fastPeriod": 12,
    "slowPeriod": 26
  }
}
```

### Insufficient history

After accept/fetch, if closed candle count `< slowPeriod` (from effective
params; default 21), fail with `insufficient_history` per Feature 004
persistence rules (durable `failed` row if already `running`).

### Response run object (excerpt)

```json
{
  "id": "…",
  "strategyId": "dual_ema",
  "strategyParams": {
    "fastPeriod": 12,
    "slowPeriod": 26
  },
  "status": "completed"
}
```

---

## Alias resolution matrix

| Request `strategyId` | Params | Persisted id | Effective params |
|----------------------|--------|--------------|------------------|
| `dual_ema` | omitted | `dual_ema` | `{9, 21}` |
| `dual_ema` | `{12, 26}` valid | `dual_ema` | `{12, 26}` |
| `dual_ema_9_21` | omitted | `dual_ema` | `{9, 21}` |
| `dual_ema_9_21` | `{5, 20}` valid | `dual_ema` | `{5, 20}` |
| omitted | — | — | reject |
| `unknown` | — | — | reject |

---

## GET session / GET backtest run

Must return `strategyId` (canonical preferred) and `strategyParams` (effective
or defaulted) for inspectability (FR-012, SC-005).

---

## Out of contract (v1)

- `PUT` strategy mid-session
- Strategy create/upload API
- Ranking / optimization endpoints
- WebSocket strategy streaming
