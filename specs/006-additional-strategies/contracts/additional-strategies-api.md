# Contract: Additional Strategies (extends Feature 005)

**Feature**: `006-additional-strategies`  
**Date**: 2026-08-12  
**Supersedes in part**: [005 strategy-api.md](../../005-strategy-framework/contracts/strategy-api.md) list payload size and entries  
**Consumer**: Auto Trading frontend (Simulation + Backtest) and automated tests

Local/unauthenticated. No new endpoints. Simulation/backtest create already
accept `strategyId` + optional `strategyParams` for any registered id.

---

## `GET /strategies`

**Change**: Response MUST include **exactly five** strategies when Feature 006
is fully registered (Dual EMA + four new). Order is not significant for
correctness; recommended stable order for UX/tests:

1. `dual_ema`
2. `rsi`
3. `macd`
4. `bollinger_bands`
5. `breakout`

### New entries (schemas)

#### RSI

```json
{
  "id": "rsi",
  "displayName": "RSI",
  "aliases": [],
  "parameters": [
    {
      "name": "period",
      "type": "integer",
      "label": "RSI period",
      "default": 14,
      "minimum": 2
    },
    {
      "name": "overbought",
      "type": "integer",
      "label": "Overbought",
      "default": 70,
      "minimum": 1,
      "maximum": 99
    },
    {
      "name": "oversold",
      "type": "integer",
      "label": "Oversold",
      "default": 30,
      "minimum": 1,
      "maximum": 99
    }
  ],
  "constraints": [
    {
      "code": "oversold_lt_overbought",
      "message": "Oversold threshold must be less than overbought threshold.",
      "fields": ["oversold", "overbought"]
    }
  ]
}
```

#### MACD

```json
{
  "id": "macd",
  "displayName": "MACD",
  "aliases": [],
  "parameters": [
    {
      "name": "fastPeriod",
      "type": "integer",
      "label": "Fast period",
      "default": 12,
      "minimum": 1
    },
    {
      "name": "slowPeriod",
      "type": "integer",
      "label": "Slow period",
      "default": 26,
      "minimum": 2
    },
    {
      "name": "signalPeriod",
      "type": "integer",
      "label": "Signal period",
      "default": 9,
      "minimum": 1
    }
  ],
  "constraints": [
    {
      "code": "fast_lt_slow",
      "message": "Fast period must be less than slow period.",
      "fields": ["fastPeriod", "slowPeriod"]
    }
  ]
}
```

#### Bollinger Bands

```json
{
  "id": "bollinger_bands",
  "displayName": "Bollinger Bands",
  "aliases": [],
  "parameters": [
    {
      "name": "period",
      "type": "integer",
      "label": "Period",
      "default": 20,
      "minimum": 2
    },
    {
      "name": "stdDev",
      "type": "decimal_string",
      "label": "Std deviations",
      "default": "2.0",
      "minimum": 0
    }
  ],
  "constraints": []
}
```

Notes for `stdDev`:
- Type is `decimal_string`; default `"2.0"`.
- Server MUST reject values ≤ 0 (bounds message). UI `minimum: 0` is advisory;
  exclusive lower bound is enforced server-side.

#### Breakout

```json
{
  "id": "breakout",
  "displayName": "Breakout",
  "aliases": [],
  "parameters": [
    {
      "name": "lookback",
      "type": "integer",
      "label": "Lookback",
      "default": 20,
      "minimum": 2
    }
  ],
  "constraints": []
}
```

Dual EMA entry remains as documented in Feature 005 (unchanged).

---

## Simulation / Backtest create

`POST /simulation/sessions` and `POST /backtest/runs` — no field shape change.

| `strategyId` | Accepted |
|--------------|----------|
| `dual_ema` / alias `dual_ema_9_21` | Yes (existing) |
| `rsi` | Yes |
| `macd` | Yes |
| `bollinger_bands` | Yes |
| `breakout` | Yes |
| unknown / omitted | Reject (existing Feature 005 rules) |

Invalid `strategyParams` for the chosen strategy → `400` with
`invalid_strategy_params` (or equivalent) and the constraint message.

Persisted response fields (existing):

- `strategyId` — canonical id
- `strategyParams` — effective parameters object

### Example — create simulation with RSI defaults

```json
{
  "strategyId": "rsi",
  "symbol": "BTCUSDT",
  "timeframe": "1m"
}
```

(Other required session fields per Feature 003 unchanged.)

### Example — create backtest with Bollinger custom stdDev

```json
{
  "strategyId": "bollinger_bands",
  "strategyParams": { "period": 20, "stdDev": "2.5" }
}
```

(Other required backtest fields per Feature 004 unchanged.)

---

## Error examples

| Case | Expected |
|------|----------|
| RSI `oversold: 70`, `overbought: 70` | Reject; message includes oversold &lt; overbought |
| MACD `fastPeriod: 26`, `slowPeriod: 12` | Reject; fast &lt; slow |
| Bollinger `stdDev: "0"` | Reject; stdDev must be &gt; 0 |
| Breakout `lookback: 1` | Reject; minimum 2 |
| Backtest window candles &lt; strategy `S` | `insufficient_history` |

---

## Frontend fallback catalog

`FALLBACK_STRATEGIES` MUST include the same five schemas so the selector
remains usable if `GET /strategies` fails or is still loading. Live API remains
source of truth when available.
