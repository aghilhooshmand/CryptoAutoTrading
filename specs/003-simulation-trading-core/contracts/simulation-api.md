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
| `mode` | `"simulation"` |

> **Superseded by Feature 005** (`specs/005-strategy-framework/`): Feature 003
> documented an implicit default `strategyId` of `"dual_ema_9_21"` when omitted.
> That default is **withdrawn**. `strategyId` is now **required** on create
> (omit → reject). New creates MUST persist the canonical id `dual_ema`
> (legacy alias `dual_ema_9_21`, when explicitly supplied, still resolves to
> Dual EMA). See `specs/005-strategy-framework/contracts/strategy-api.md`.

`mode: "real_money"` MUST be rejected at create/start with
`real_money_unavailable`. Feature 003 does not implement real XT execution.

### Amendment 2026-08-17 — Product identity (C1)

Create and read MUST support:

| Field | Notes |
|-------|--------|
| `venue` | `kraken` (new default) or `xt` (legacy). Omit + XT-form `symbol` (e.g. `btc_usdt`) ⇒ infer `venue=xt`. Omit + no XT-form symbol on a **new** create ⇒ `venue=kraken` when other identity fields or Settings supply a Kraken product. |
| `baseAsset` | Canonical base (e.g. `BTC`) |
| `quoteAsset` | From the selected product (not assumed USDT or EUR) |
| `canonicalSymbol` | Operator identity (e.g. `BTC/EUR`) |
| `venueProductId` | Adapter wire id (Kraken pair id, or XT `btc_usdt`) |

`symbol` is a **compatibility alias** only. New Kraken-default creates MUST
persist and return the identity fields above; `symbol` MAY echo
`canonicalSymbol`. Do **not** rewrite historical sessions. NULL-venue rows
with XT-form `symbol` keep working as `venue=xt`.

---

### `maxTrades`

Limits **strategy-driven** fills only. After `strategyFillCount` reaches
`maxTrades`, no further strategy execution is allowed. If the session is LONG,
one forced safety close is still allowed and may make `tradeCount` equal
`maxTrades + 1`; that trade MUST have `isForcedClose: true`.

### Capital nesting

Create/start MUST enforce:

```text
0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital
```

Violations → HTTP `400` / `invalid_config`.

### Profit / loss rates

Operator configures `targetNetProfitRate` and `maxSessionLossRate` as fractions
of `allocatedCapital` (e.g. `"0.01"` = 1.0%). Server derives, **persists**, and
returns absolute amounts:

```text
targetNetProfitAmount = allocatedCapital * targetNetProfitRate
maxSessionLossAmount  = allocatedCapital * maxSessionLossRate
```

Hard limits compare liquidation-based Session NET P&L to these amounts.
Frontend MUST display both percentage and currency amount.

### Forced close on stop

`POST .../stop`, `POST .../emergency-stop`, and automatic hard stops share one
path: if LONG and a safe price exists → exactly one forced full simulated SELL
(`isForcedClose: true`); if no safe price → `unsafe_unflattened` (never invent
an exit). No further strategy-driven fills after stop.

---

## `POST /simulation/sessions`

Create a session in `CONFIGURED`.

### Request body

```json
{
  "mode": "simulation",
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "strategyId": "dual_ema",
  "startingCapital": "500",
  "allocatedCapital": "500",
  "maxPositionSize": "500",
  "targetNetProfitRate": "0.01",
  "maxSessionLossRate": "0.007",
  "maxTrades": 20,
  "durationSeconds": 3600,
  "feeRate": "0.001",
  "slippageRate": "0.0005",
  "decisionLogMode": "important_only"
}
```

`strategyId` is **required** as of Feature 005 (canonical `dual_ema`; see
supersession note under Defaults). Optional `strategyParams` may be omitted to
apply registry defaults for that strategy.

Optional `decisionLogMode`: `"important_only"` \| `"full_audit"`. When omitted
on **create**, server MUST persist effective **`important_only`** for new
sessions (typically seeded from Settings default). Invalid value → `400`
`invalid_config`. Legacy rows with NULL mode behave as `full_audit` on read
and for persistence gating.

`allocatedCapital` is required for enforceable sizing (MUST NOT deploy above it).
If omitted, server MAY default it to `startingCapital`, but the field remains
distinct and MUST still satisfy
`0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital`. Server MUST persist
derived `targetNetProfitAmount` and `maxSessionLossAmount` (example: `"5"` and
`"3.5"` for the rates above) together with the configured rates.

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

Manual stop: `RUNNING` → `STOPPING` → `STOPPED`. Uses the **same** forced-close
path as emergency/automatic hard stops: if LONG and safe price → exactly one
forced full SELL (`isForcedClose: true`); else `unsafe_unflattened` (no invented
exit).

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
  "strategyId": "dual_ema",
  "startingCapital": "500",
  "allocatedCapital": "500",
  "maxPositionSize": "500",
  "targetNetProfitRate": "0.01",
  "maxSessionLossRate": "0.007",
  "targetNetProfitAmount": "5",
  "maxSessionLossAmount": "3.5",
  "maxTrades": 20,
  "durationSeconds": 3600,
  "feeRate": "0.001",
  "slippageRate": "0.0005",
  "decisionLogMode": "important_only",
  "cash": "500",
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
    "startEquity": "500",
    "cash": "500",
    "markEquity": "500",
    "markNetPnl": "0",
    "unrealizedGross": "0",
    "liquidationEquity": "500",
    "grossPnl": "0",
    "fees": "0",
    "slippageCost": "0",
    "netPnl": "0",
    "targetNetProfitRate": "0.01",
    "targetNetProfitAmount": "5",
    "maxSessionLossRate": "0.007",
    "maxSessionLossAmount": "3.5",
    "markPrice": "65000.00",
    "markSafe": true
  },
  "label": "SIMULATION"
}
```

`economics.netPnl` is the **hard-limit** Session NET (`liquidationEquity -
startEquity`) and is compared to `targetNetProfitAmount` /
`maxSessionLossAmount`. `markEquity` / `markNetPnl` / `unrealizedGross` are
informational. When mark unsafe while long: `netPnl`, `liquidationEquity`, and
mark fields that require a price MAY be `null` with `markSafe: false`.

`lastProcessedCandleOpenTime` is the duplicate-candle cursor: the same closed
candle MUST NOT be evaluated twice. It MUST advance for processed HOLD candles
even when `decisionLogMode` is `important_only` and no HOLD Decision Journal
row is written.

`decisionLogMode` is effective configuration. GET responses MUST return the
effective mode (`important_only` or `full_audit`); legacy NULL storage MUST be
presented as `full_audit`.

Hypothetical liquidation costs used to evaluate profit/loss stops are not
separate ledger entries; an actual forced close applies fee/slippage once.
---

## `GET /simulation/sessions/{id}/decisions`

Returns **durably persisted** Decision Journal rows only (no fabricated HOLDs).
Under `important_only`, ordinary HOLD evaluations do not appear. Under
`full_audit`, HOLD rows appear as historically required.

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
| FR-010–011 | decisions + trades; decisionLogMode gates durable HOLD |
| FR-005 | capital nesting `0 < maxSize ≤ allocated ≤ starting`; rates + amounts persisted |
| FR-005a | BUY sizing `min(affordable, allocated, maxSize)` |
| FR-006a | persist `lastProcessedCandleOpenTime`; no duplicate candle eval |
| FR-012a | fee/slippage defaults |
| FR-014 | `netPnl` / limits use liquidation equity vs derived absolute thresholds |
| FR-014a | forced close vs max_trades |
| FR-015–016 | stop / emergency-stop; no new **strategy-driven** exec when stopped |
| FR-015a | manual/emergency/hard stop share forced close; `isForcedClose` |
| SC-007 | no private XT trading routes; real_money rejected at API |
