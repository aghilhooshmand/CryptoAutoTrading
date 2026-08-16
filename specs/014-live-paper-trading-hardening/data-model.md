# Data Model: Feature 014 — Live Paper-Trading Hardening

**Date**: 2026-08-16  
**Storage**: Existing Simulation SQLite (Feature 003+); extend session lifecycle
and audit; Simulation Portfolio (009) remains separate book — reconciled, not
merged with Real XT.

See [research.md](./research.md) R2–R4 and [contracts/simulation-recovery-api.md](./contracts/simulation-recovery-api.md).

---

## Entities

### SimulationSession (extended)

Existing fields retained (`cash`, `position_*`, `allocation_id`,
`last_processed_candle_open_time`, `unsafe_quote_streak`,
`position_flatten_status`, `stop_reason`, journals linkage, etc.).

| Field | Type | Rules |
|-------|------|--------|
| state | enum | `CONFIGURED` \| `RUNNING` \| `STOPPING` \| `RECOVERY_BLOCKED` \| `STOPPED` |
| recovery_reason | string \| null | Stable code when entering/remaining `RECOVERY_BLOCKED`; null when not blocked |
| recovery_detail | string \| null | Optional operator-readable detail; no secrets; may list failed gate codes |
| last_recovery_at | datetime \| null | Last startup or resume reconcile attempt |

**Validation**:
- `allows_strategy_execution` only when `state == RUNNING`.
- At most one session in `{RUNNING, STOPPING, RECOVERY_BLOCKED}` (active slot).
- `STOPPED` remains terminal (no transition to `RUNNING` except via new session;
  resume is only from `RECOVERY_BLOCKED`).

---

### SessionState transitions

```text
CONFIGURED → RUNNING                 (start)
RUNNING → STOPPING                   (stop / emergency / unsafe-streak stop)
STOPPING → STOPPED                   (stop complete)
RUNNING|STOPPING → RECOVERY_BLOCKED  (startup reconcile fail)
RUNNING|STOPPING → RUNNING           (startup reconcile pass — may be same state)
RECOVERY_BLOCKED → RUNNING           (operator resume + gates pass)
RECOVERY_BLOCKED → STOPPING          (operator stop / emergency)
STOPPED → (none)
```

Illegal transitions raise / return fail-closed API errors.

---

### ReconcileResult (runtime, may be logged / returned)

| Field | Type | Rules |
|-------|------|--------|
| passed | bool | True only if all gates pass |
| failed_gates | string[] | Stable codes from research R3 |
| session_id | string | Required |
| checked_at | datetime | Server time |

Gate codes:
- `reconcile_session_journal_mismatch`
- `reconcile_watermark_inconsistent`
- `reconcile_portfolio_mismatch`
- `reconcile_unsafe_unflattened`
- `reconcile_mark_untrustworthy`
- `recovery_gap_unresolvable` (gap skip cannot be proven)

---

### SkippedGapAudit

Persisted evidence of offline candles intentionally not traded (FR-010).

| Field | Type | Rules |
|-------|------|--------|
| id | string/uuid | PK |
| session_id | string | FK session |
| from_open_time | datetime \| null | Prior watermark (exclusive lower bound); null if none |
| to_open_time | datetime | New watermark after skip (latest closed candle open_time used) |
| reason | string | `offline_gap_skip` |
| recorded_at | datetime | When advance committed |

**Validation**: Written only after successful reconcile and only when
`to_open_time` advances past prior watermark. Never implies fills were created
for the gap.

---

### Candle watermark

| Field | Location | Rules |
|-------|----------|--------|
| last_processed_candle_open_time | session | Cursor; after tick or skip-advance; reprocessing ≤ watermark must not create fills |

---

### DecisionJournal / TradeJournal (strengthened)

Existing append-only journals. Feature 014 adds **duplicate safety**:

| Constraint | Rule |
|------------|------|
| Trade uniqueness | Unique `(session_id, candle_open_time, is_forced_close)` (or equivalent) so restart/retry cannot insert a second fill for the same logical event |
| Decision uniqueness | Unique `(session_id, candle_open_time)` for persisted decision rows when inserted |
| HOLD path | May omit decision row (`important_only`) but still advances watermark — reconcile must accept watermark ahead of last decision when last event was HOLD |

Never invent journal rows for offline gaps.

---

### Simulation Portfolio binding (reconcile subject)

| Concept | Rules |
|---------|--------|
| allocation_id | Optional bind to Feature 009 allocation |
| G3 | Bound session cash/position must agree with Portfolio USDT + base holding; unbound long with Portfolio projection conflict fails |
| Isolation | Real XT (013) never written into Simulation Portfolio during recovery |

---

### Market-data health (mark safety)

| Status | Simulation meaning |
|--------|-------------------|
| Trustworthy / FRESH | Eligible mark for valuation / flatten |
| Stale / unavailable / error | Unsafe; block new entries; increment `unsafe_quote_streak`; no invented price |

`UNSAFE_QUOTE_LIMIT = 3` retained.

---

## State × trading matrix

| State | Strategy entries | Forced flatten | Operator resume | History “complete” |
|-------|------------------|----------------|-----------------|--------------------|
| CONFIGURED | No | No | N/A | No |
| RUNNING | Yes | On stop if safe mark | N/A | No |
| STOPPING | No | In progress | No | No |
| RECOVERY_BLOCKED | No | On operator stop if safe mark | Yes (re-gate) | No |
| STOPPED | No | Done | No | Yes |

---

## Persistence notes

- Prefer single transaction: fill + portfolio apply + journals + watermark.
- Startup recovery commits `RECOVERY_BLOCKED` or resumed `RUNNING` + optional
  SkippedGapAudit before worker may trade.
- Mid-fill crash: reconcile detects journal/session/Portfolio mismatch →
  `RECOVERY_BLOCKED` (no invent).
