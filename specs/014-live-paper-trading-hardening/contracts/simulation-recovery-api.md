# Contract: Simulation Recovery & Resume API

**Feature**: `014-live-paper-trading-hardening`  
**Date**: 2026-08-16  
**Consumer**: Auto Trading UI (session status / history)  
**Depends on**: Existing `/simulation` routes; Feature 009 Portfolio; public market data  
**Non-goals**: Real trading; XT private APIs; inventing fills/balances

Local/unauthenticated operator API. JSON **camelCase**. Decimal money as
**strings**. Fail closed — never invent prices, fills, or Portfolio corrections.

---

## Session state values

| state | Meaning |
|-------|---------|
| `CONFIGURED` | Created, not started |
| `RUNNING` | Strategy execution allowed |
| `STOPPING` | Stop in progress |
| `RECOVERY_BLOCKED` | Non-trading; reconcile failed or incomplete; operator action required |
| `STOPPED` | Terminal normal/forced completion (History) |

---

## Session status fields (extended)

Existing session payload fields retained. Additions:

| Field | Type | Notes |
|-------|------|--------|
| `state` | string | Includes `RECOVERY_BLOCKED` |
| `recoveryReason` | string \| null | Stable code when blocked / last failed resume |
| `recoveryDetail` | string \| null | Human-readable; may list gate codes; no secrets |
| `lastRecoveryAt` | ISO-8601 \| null | Last reconcile attempt |
| `lastProcessedCandleOpenTime` | ISO-8601 \| null | Watermark (existing) |
| `positionFlattenStatus` | string | Includes `unsafe_unflattened` |
| `skippedGap` | object \| null | Latest skip audit summary if any |

### `skippedGap` object

```json
{
  "fromOpenTime": "2026-08-16T10:00:00.000Z",
  "toOpenTime": "2026-08-16T12:00:00.000Z",
  "reason": "offline_gap_skip",
  "recordedAt": "2026-08-16T12:00:05.000Z"
}
```

---

## POST `/simulation/sessions/{id}/resume`

Resume a **`RECOVERY_BLOCKED`** session after re-running full reconciliation
(FR-006) and offline-gap skip if needed.

### Preconditions

- Session `state == RECOVERY_BLOCKED`
- No other session occupies the active slot in a conflicting way (same single-active rules)

### Success 200

Session returns to `RUNNING`; `recoveryReason` cleared (or null); worker may
process **new** closed candles after watermark only.

```json
{
  "id": "…",
  "state": "RUNNING",
  "recoveryReason": null,
  "lastProcessedCandleOpenTime": "2026-08-16T12:00:00.000Z",
  "skippedGap": {
    "fromOpenTime": "2026-08-16T10:00:00.000Z",
    "toOpenTime": "2026-08-16T12:00:00.000Z",
    "reason": "offline_gap_skip",
    "recordedAt": "2026-08-16T12:00:05.000Z"
  }
}
```

### Failure — still blocked 409 (typical)

```json
{
  "error": {
    "code": "recovery_still_blocked",
    "message": "Reconciliation did not pass; session remains RECOVERY_BLOCKED.",
    "failedGates": ["reconcile_portfolio_mismatch"]
  },
  "session": {
    "id": "…",
    "state": "RECOVERY_BLOCKED",
    "recoveryReason": "reconcile_portfolio_mismatch"
  }
}
```

### Other errors

| code | HTTP | Meaning |
|------|------|---------|
| `session_not_found` | 404 | Unknown id |
| `invalid_state_for_resume` | 409 | Not `RECOVERY_BLOCKED` (e.g. `STOPPED`) |
| `recovery_gap_unresolvable` | 409 | Cannot prove skip bounds; remain blocked |

---

## Stop / emergency stop from `RECOVERY_BLOCKED`

Existing:

- `POST /simulation/sessions/{id}/stop`
- `POST /simulation/sessions/{id}/emergency-stop`

**Extension**: Both MUST accept `RECOVERY_BLOCKED` (and existing `RUNNING`),
transition via `STOPPING` → `STOPPED`, prevent new entries, flatten only with
trustworthy mark else `unsafe_unflattened`.

---

## Startup recovery (internal contract)

On backend lifespan, before worker trades:

1. Select orphaned active sessions (`RUNNING` / `STOPPING` from prior process).
2. Reconcile (FR-006).
3. Pass → gap skip + watermark advance + audit → `RUNNING`.
4. Fail → `RECOVERY_BLOCKED` + `recoveryReason` / gate codes.
5. Never invent fills for downtime; never merge Real XT into Simulation Portfolio.

Observable via `GET /simulation/sessions/{id}` and `/sessions/active` (active
listing SHOULD include `RECOVERY_BLOCKED` so operators see the blocked session).

---

## GET active session

`GET /simulation/sessions/active` MUST surface `RECOVERY_BLOCKED` when that is
the occupying session (not only `RUNNING`/`STOPPING`), so UI can show Resume /
Stop without appearing “idle.”

---

## Stable recovery / reconcile codes

| code | Meaning |
|------|---------|
| `reconcile_session_journal_mismatch` | Session cash/position ≠ journals |
| `reconcile_watermark_inconsistent` | Watermark vs journals unsafe |
| `reconcile_portfolio_mismatch` | Simulation Portfolio disagree |
| `reconcile_unsafe_unflattened` | Unresolved unsafe flatten |
| `reconcile_mark_untrustworthy` | Long position needs mark; mark unsafe |
| `recovery_gap_unresolvable` | Cannot identify offline skip range |
| `recovery_still_blocked` | Resume attempted; gates still fail |
| `invalid_state_for_resume` | Resume on wrong state |
