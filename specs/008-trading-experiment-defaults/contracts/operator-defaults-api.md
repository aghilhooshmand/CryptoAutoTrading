# Contract: Operator Defaults (Settings) API

**Feature**: `008-trading-experiment-defaults`  
**Date**: 2026-08-12  
**Consumer**: Auto Trading frontend (Settings tab + create-form seeders)  
**Depends on**: Feature 005/006 `GET /strategies` / `validate_and_materialize`

Local/unauthenticated. No WebSockets. No trading side effects.

Field names are camelCase JSON, aligned with Simulation / Backtest /
Comparison create bodies.

---

## Settings body (shared)

```json
{
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startingCapital": "1000",
  "allocatedCapital": "1000",
  "maxPositionSize": "1000",
  "feeRate": "0.002",
  "slippageRate": "0.0005",
  "targetNetProfitRate": null,
  "maxSessionLossRate": null,
  "maxTrades": null,
  "strategyId": "dual_ema",
  "strategyParams": { "fastPeriod": 9, "slowPeriod": 21 },
  "decisionLogMode": "important_only",
  "updatedAt": "2026-08-12T12:00:00.000Z",
  "source": "saved",
  "warning": null
}
```

| Field | Notes |
|-------|--------|
| Optional risk / `maxTrades` | `null` or omitted ⇒ unset (not zero) |
| `decisionLogMode` | `"important_only"` \| `"full_audit"`; product starter **`important_only`**; Simulation create seed only (not Backtest) |
| `source` | `"saved"` \| `"starters"` (read responses) |
| `warning` | Optional string when read fail-closed to starters |
| `updatedAt` | Present for saved rows; may be null/omitted for pure starter responses before first Save/Reset |

---

## `GET /settings`

Return the effective defaults used to initialize **fresh** create forms.

| Case | Behavior |
|------|----------|
| No row / empty DB | `200` + product starters, `source: "starters"` |
| Valid saved row | `200` + row, `source: "saved"` |
| Corrupt / invalid stored payload | `200` + product starters, `source: "starters"`, non-null `warning` |

MUST NOT mutate storage on GET. MUST NOT start trading.

---

## `PUT /settings`

Explicit Save. Replace the singleton Settings with the request body after
validation.

### Request body

Same fields as Settings body **except** `source`, `warning`, and `updatedAt`
(server sets `updatedAt`). Optional risk fields may be `null` or omitted.

### Success

`200` with full Settings body, `source: "saved"`, fresh `updatedAt`.

### Errors (leave last good Settings unchanged)

| Condition | Status | Error code (typical) |
|-----------|--------|----------------------|
| Capital nesting violation | `400` | `invalid_config` |
| Bad fee/slippage / rate parse | `400` | `invalid_config` |
| Unknown strategy | `400` | `unknown_strategy` |
| Invalid strategy params | `400` | `invalid_strategy_params` |
| Invalid symbol / timeframe | `400` | `invalid_config` |

Error shape matches existing APIs:

```json
{
  "detail": {
    "error": {
      "code": "invalid_config",
      "message": "…"
    }
  }
}
```

MUST NOT start, stop, or modify any simulation, backtest, or comparison.

---

## `POST /settings/reset`

Persist product starter defaults as the active Settings (after confirmation in
UI). Equivalent to saving starters explicitly.

### Success

`200` with starter field values, `source: "saved"` (or `source: "starters"` if
product equates cleared-custom with starters — prefer **`saved`** after Reset
so `updatedAt` reflects the reset), `warning: null`.

### Side effects

MUST NOT create, stop, or modify trading artifacts.

---

## Frontend contracts (non-HTTP)

### Settings tab

- Hosted under Auto Trading as a tab (not a 4th primary nav area).
- Explicit **Save** and **Reset** (Reset confirms before calling
  `POST /settings/reset`).
- Unsaved draft edits MUST NOT affect create-form initialization (forms read
  last successful `GET` / saved state only after Save).
- Unsaved Settings draft MUST survive Auto Trading tab switches until Save,
  Reset, or full page reload (no auto-save / auto-discard on tab leave).
- When `GET /settings` returns a non-null `warning`, Settings UI MUST show it
  with the returned starter values (FR-014).
- Changing preferred strategy in the draft resets params to registry defaults
  (reuse `StrategyConfigFields` behavior).
- Usable at ~375px; no hover-only Save/Reset.

### Create-form initialization

| Form | Mapping from Settings |
|------|------------------------|
| Simulation | Shared market/money/cost/optional risk + strategy + **`decisionLogMode`** (default `important_only`); leave unset optionals empty; **do not** invent rates; keep Simulation required validation at submit; operator may override `decisionLogMode` on the create form |
| Backtest | Same shared fields + strategy; omit unset optionals from create body; **do not** apply `decisionLogMode` to Backtest |
| Comparison | Shared market/money/cost/optional risk; **leg 0** = Settings strategy/params; **leg 1+** = product/registry starters; **no** `decisionLogMode` |

Apply only on **fresh** draft open / post-create form reset. Never overwrite an
in-progress draft when Settings change.

### Historical artifacts

No Settings API call is required to display historical effective configs.
Changing Settings MUST leave existing Session / Run / Comparison rows unchanged
(verified by re-GET of those resources).

---

## Out of scope for this contract

- Cloud sync, auth, multi-user profiles
- Exchange credentials / API keys / real-money enablement
- GE experiment defaults (seed, population, generations)
- Default historical window start/end
- WebSocket push of Settings changes
