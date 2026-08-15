# Contract: Simulation History API

**Feature**: `011-simulation-history-results`  
**Date**: 2026-08-15  
**Consumer**: Auto Trading frontend and automated tests  
**Extends**: `specs/003-simulation-trading-core/contracts/simulation-api.md`
(and Feature 010 session field additions)

Base path: `/simulation`  
Content-Type: `application/json`  
Money/rates: decimal strings. Local/unauthenticated single-operator.

Existing create/start/stop/emergency-stop/active/journals remain unless noted.
This contract adds **list**, **delete**, and **`finalResult`** on detail.

**Terminology — recovery**: Fail-closed orphan handling
(`RUNNING`/`STOPPING` → `STOPPED`) plus final-result freeze/backfill. Does
**not** mean resume, restart of the same session id, or worker recreation.

---

## `finalResult` object

Present on STOPPED sessions after freeze/backfill; absent/null otherwise.

```json
{
  "complete": true,
  "frozenAt": "2026-08-15T12:00:00Z",
  "source": "stop",
  "startingCapital": "10000",
  "endingEquity": "10050.12",
  "netPnl": "50.12",
  "returnPct": "0.005012",
  "cash": "10050.12",
  "fees": "1.20",
  "slippageCost": "0.40",
  "tradeCount": 4,
  "strategyFillCount": 4,
  "positionFlattenStatus": "flat",
  "stopReason": "operator_stop",
  "markEquity": null,
  "markPrice": null
}
```

Incomplete example: `complete: false`, `endingEquity`/`netPnl`/`returnPct` =
`null`, other truthful fields still set.

### STOPPED detail economics rule

When `finalResult` is present, it is the **sole authoritative** ending
economics for History/detail. The STOPPED History detail response MUST NOT
expose current/live mark-based ending equity, net P&L, or return that can
drift after termination (omit a drifting `economics` ending block for
STOPPED, or omit mark-derived ending fields). RUNNING/STOPPING may continue
to use live `economics`.

---

## `GET /simulation/sessions`

List persisted sessions (History).

### Query

| Param | Required | Default | Notes |
|-------|----------|---------|-------|
| `state` | no | — | One of `CONFIGURED` \| `RUNNING` \| `STOPPING` \| `STOPPED` |
| `limit` | no | `50` | Page size; maximum **100**; values above max → `400` `invalid_query` |
| `offset` | no | `0` | Non-negative skip count; negative → `400` `invalid_query` |

Ordering is locked: **`created_at DESC`, then `id DESC`**.  
No server FIFO eviction — older sessions remain reachable via higher `offset`.

### Success — HTTP `200`

```json
{
  "sessions": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "state": "STOPPED",
      "symbol": "btc_usdt",
      "timeframe": "1h",
      "strategyId": "dual_ema",
      "startedAt": "2026-08-15T11:00:00Z",
      "stoppedAt": "2026-08-15T11:30:00Z",
      "stopReason": "operator_stop",
      "createdAt": "2026-08-15T10:59:00Z",
      "finalResultSummary": {
        "complete": true,
        "netPnl": "50.12",
        "returnPct": "0.005012"
      }
    }
  ],
  "totalCount": 120,
  "limit": 50,
  "offset": 0
}
```

- `totalCount`: total matching rows (after `state` filter if any), independent
  of `limit`/`offset`.
- Missing freeze on STOPPED: server MUST backfill ledger-only before/within
  response so STOPPED items expose summary when reconstructible (or
  `complete: false` summary).
- `finalResultSummary` may be null for CONFIGURED/RUNNING/STOPPING.

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Invalid `state` | `400` | `invalid_query` |
| `limit` > 100 or `limit` < 1 | `400` | `invalid_query` |
| `offset` < 0 | `400` | `invalid_query` |

---

## `GET /simulation/sessions/{id}`

Existing detail. **Additive**: include `finalResult` when available.

### Success — HTTP `200`

Full session resource as today for CONFIGURED/RUNNING/STOPPING (config,
Feature 010 fields, journals via sibling endpoints) **plus** for STOPPED:

```json
{
  "finalResult": { "...": "see above" }
}
```

- STOPPED without JSON: ledger-only backfill then return.
- STOPPED with `finalResult`: authoritative ending economics from
  `finalResult` only (see economics rule above).
- CONFIGURED/RUNNING: `finalResult` null/absent.

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `session_not_found` |

---

## `GET /simulation/sessions/{id}/trades`

Unchanged (Feature 003). Required for History detail.

---

## `GET /simulation/sessions/{id}/decisions`

Unchanged transport (Feature 003). Required for History detail. Returns
**only durably persisted** rows — History MUST NOT fabricate HOLDs.
Effective `decisionLogMode` on the session explains sparse vs dense journals.
MUST continue to return Risk `reasonCode` / `reasonMessage` when recorded.

---

## `GET /simulation/sessions/active`

Unchanged. Required for reconnect after refresh (FR-017).

---

## `DELETE /simulation/sessions/{id}`

Delete a historical (or never-started) session and its journals.

### Success

- HTTP `204` — no body
- Session and session-scoped journals removed
- Portfolio balances / allocations unchanged

### Errors

| Condition | HTTP | `error.code` |
|-----------|------|--------------|
| Not found | `404` | `session_not_found` |
| `RUNNING` or `STOPPING` | `409` | `session_active` |
| Portfolio binding still has reserved or deployed capital for this session | `409` | `portfolio_binding_active` |

Delete MUST NOT release/unwind Portfolio capital.

---

## Freeze side effects (existing stop paths)

`POST .../stop`, `POST .../emergency-stop`, automatic hard stops, and startup
**recovery** that set `STOPPED` MUST persist `finalResult` before/at commit of
STOPPED (see research Decision 11).

No new public “freeze”, “resume”, or “restart historical session” endpoint.

---

## Frontend route contract (non-HTTP)

| Surface | Requirement |
|---------|-------------|
| History list | On Auto Trading → Simulation tab; must paginate via `offset`/`limit` using `totalCount` so older sessions are reachable |
| Detail | Dedicated route **`/auto-trading/simulation/:sessionId`** |
| Top-level nav | MUST NOT add a new primary nav item only for Simulation History |
| CONFIGURED actions | May use existing Feature 003 **Start** (reuse; no second start stack) |
| STOPPED actions | Inspect + delete confirm only — no restart / resume / run-again |
| Decision journal | Persisted rows only; show effective `decisionLogMode`; no fabricated HOLDs |
| Refresh | MUST NOT POST stop solely due to remount/refresh |

---

## Error envelope

Same as Feature 003:

```json
{
  "error": {
    "code": "portfolio_binding_active",
    "message": "Human-readable explanation"
  }
}
```
