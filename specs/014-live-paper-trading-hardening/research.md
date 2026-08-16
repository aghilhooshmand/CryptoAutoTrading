# Research: Feature 014 — Live Paper-Trading Hardening

**Date**: 2026-08-16  
**Branch**: `014-live-paper-trading-hardening`  
**Sources**: Clarified `spec.md` (Session 2026-08-16); repository baseline
(`recovery.py`, `state_machine.py`, `pipeline.py`, `worker.py`,
`XtSpotAdapter`); Features 003/009/010/011/012/013; constitution I–IV, VIII–IX,
XXXII, XXXIV.

---

## R1 — Replace orphan→STOPPED with conditional recovery

**Decision**: Replace `recover_orphan_sessions` “always STOPPED + never resume”
with startup **recover-and-reconcile**:

1. Find sessions that were active across process death (`RUNNING` / `STOPPING`,
   and any in-flight recovery flags if present).
2. Run deterministic reconciliation (FR-006).
3. If all gates pass → complete offline-gap skip (FR-010) → return session to
   `RUNNING` and let the existing worker tick continue (conditional safe
   auto-recovery).
4. If any gate fails → `RECOVERY_BLOCKED` (non-trading); no strategy execution;
   operator must resume (re-gate) or stop/close / start new.

**Rationale**: Spec clarification Option C + Option B for fail-closed state.
Baseline orphan stop remains the *safety idea* (never invent / never silent
trade) but is insufficient for long-running paper trading when ledgers are
actually consistent.

**Alternatives considered**:
- Keep always-STOPPED (baseline) — rejected by clarify.
- Always auto-resume without gates — rejected (capital protection).
- Operator confirmation even when safe — rejected (clarify chose conditional
  auto-recovery).

---

## R2 — `RECOVERY_BLOCKED` lifecycle

**Decision**: Extend session state machine with **`RECOVERY_BLOCKED`**:

| From | To | Trigger |
|------|----|---------|
| `RUNNING` / `STOPPING` (orphan) | `RECOVERY_BLOCKED` | Startup reconcile fail |
| `RUNNING` / `STOPPING` (orphan) | `RUNNING` | Startup reconcile pass (+ gap skip) |
| `RECOVERY_BLOCKED` | `RUNNING` | Operator `POST .../resume` after full FR-006 pass |
| `RECOVERY_BLOCKED` | `STOPPING` → `STOPPED` | Operator stop / emergency stop / close-out path |
| `STOPPED` | ∅ | Remains terminal (Feature 011 History) |

Rules:
- `allows_strategy_execution` = **`RUNNING` only** (unchanged intent).
- `RECOVERY_BLOCKED` is **not** History “normal complete”; UI must distinguish
  from `STOPPED`.
- Active-session uniqueness: at most one of `RUNNING` | `STOPPING` |
  `RECOVERY_BLOCKED` may bind capital / block a second start (treat
  `RECOVERY_BLOCKED` as occupying the “active slot” until stopped or resumed).

**Rationale**: Clarification lock for Open #7; preserves STOPPED History
semantics.

**Alternatives considered**:
- Terminal STOPPED + distinct reason — rejected (clarify Option B).
- Stay RUNNING with a suspended flag — rejected (blurred authority; harder
  History/ops).

---

## R3 — Reconciliation gate implementation

**Decision**: Implement a pure `reconcile_session(session_id) -> ReconcileResult`
used by startup recovery and operator resume. Gates (all must pass):

| Gate | Pass condition | Fail code (stable) |
|------|----------------|--------------------|
| G1 Journals↔session | Replayed trade journal (non-forced + forced fills as recorded) matches session cash/position within exact decimal equality used elsewhere | `reconcile_session_journal_mismatch` |
| G2 Watermark↔journals | `last_processed_candle_open_time` is null only when no trade/decision candle events exist; otherwise ≥ last journaled `candle_open_time` for that session and not “behind” last fill candle | `reconcile_watermark_inconsistent` |
| G3 Portfolio | If `allocation_id` set: Portfolio USDT + base holding agree with session cash/position for bound allocation; binding still valid. If unbound: gate passes only when session is flat with no Portfolio projection conflict | `reconcile_portfolio_mismatch` |
| G4 Flatten flag | `position_flatten_status` is not `unsafe_unflattened` (and no equivalent unresolved flag) | `reconcile_unsafe_unflattened` |
| G5 Mark if long | If `position_side == long`, market quote is trustworthy (`MarketStatus.FRESH` / same mark-safety rule as pipeline) | `reconcile_mark_untrustworthy` |

On any fail: do **not** invent corrections; emit structured diagnostics; enter
`RECOVERY_BLOCKED`.

**Rationale**: Spec FR-006 Option A.

**Alternatives considered**: Soft Portfolio warn — rejected by clarify.

---

## R4 — Offline candle skip + watermark advance (deferred Open #4)

**Decision** (persistence / ordering):

1. Keep **`last_processed_candle_open_time`** as the sole trading cursor.
2. On successful reconcile, determine the **latest closed candle open_time**
   available from public market history for the session symbol/interval that is
   strictly after the prior watermark (if any).
3. If that latest closed open_time > prior watermark: set watermark to that
   latest closed open_time **without** running strategy→execution for intermediate
   candles; persist a **skipped-gap audit** record (session id, from_open_time,
   to_open_time, reason=`offline_gap_skip`, recorded_at).
4. If market history cannot identify the gap (fetch fail / empty when a gap is
   expected): **fail closed** → `RECOVERY_BLOCKED` with
   `recovery_gap_unresolvable` (do not invent skip bounds).
5. **Transaction ordering for normal ticks**: within one DB transaction (or
   equivalent atomic unit): apply fill to session + Portfolio (existing path) →
   append journals → advance watermark. Prefer advancing watermark only after
   durable journal/fill success so restart cannot “forget” a fill while
   claiming the candle done. If a fill was journaled but watermark not advanced,
   reconcile G2 / duplicate-safe journal rules prevent a second fill.
6. **Application-level idempotency**: before creating a trade for candle T,
   refuse if watermark ≥ T **or** a trade journal row already exists for
   `(session_id, candle_open_time)` for a non-forced fill of that event.
   Add a **unique constraint** on trade journal `(session_id, candle_open_time)`
   where appropriate for ordinary (non-forced) fills, **or** a partial unique
   index if forced closes must share candle identity — prefer uniqueness on
   `(session_id, candle_open_time, is_forced_close)` so forced close + signal
   fill cannot collide incorrectly. Decision journals: unique
   `(session_id, candle_open_time)` for persisted decision rows when not
   `important_only` HOLD omissions; HOLD may skip insert but still advances
   watermark (current behavior kept).

**Rationale**: Spec FR-008/009/010; closes deferred clarify #4 without inventing
fills.

**Alternatives considered**:
- Replay missed candles — rejected by clarify.
- DB unique only without watermark — insufficient for HOLD-only candles.

---

## R5 — Public market-data retry bounds (deferred Open #6)

**Decision** (implements FR-012 for **public** reads used by Simulation):

| Parameter | Value |
|-----------|--------|
| Max automatic retries | **1** (second attempt only) |
| Eligible errors | Transport timeout, connection error, HTTP 5xx, transient empty/malformed retryable adapter errors |
| Not retried | HTTP 4xx (except optionally 429 — see below), permanent adapter contract violations |
| Backoff when no Retry-After | **0.5 s** |
| If HTTP 429 / Retry-After | Wait `min(parsed, 2.0 s)`; if parsed wait would exceed **2.0 s**, **do not retry** — fail as unavailable/stale path |
| After exhausted retry | Return failure to caller; Simulation treats as unsafe/unavailable mark (no invent) |

Scope: public `XtSpotAdapter` (or a thin retry wrapper used by Simulation mark /
candle / gap-history fetches). **Do not** copy private XT trading semantics;
reads only. Retries MUST NOT re-enter strategy→execution for an already-watermarked
candle.

**Rationale**: Spec deferred Open #6; mirrors 013’s “one bounded retry” spirit
with a **stricter 2s** cap for live paper ticks (worker loop ~2s). Distinct from
private account inspect (3s).

**Alternatives considered**:
- Zero retries (baseline) — worse long-running reliability.
- N=3 exponential — rejected (duplicate-risk / hammering).
- Unlimited Retry-After — rejected (stalls fail-closed path).

---

## R6 — Stale-while-long (locked clarify)

**Decision**: Keep `UNSAFE_QUOTE_LIMIT = 3`. On unsafe/unavailable mark while
long: block new entries immediately (Risk already rejects stale); increment
streak; on exhaustion call stop path that flattens **only** with safe mark else
`unsafe_unflattened`. Do not invent exit prices. Operator-visible stop reason
`unrecoverable_unsafe_market_data` (existing) remains valid; ensure UI surfaces
flatten status.

**Rationale**: Clarification Option C; aligns with existing risk constants.

---

## R7 — Operator resume API

**Decision**: Add `POST /simulation/sessions/{id}/resume` for
`RECOVERY_BLOCKED` only. Handler re-runs full FR-006 (+ gap skip if needed);
on pass → `RUNNING` + ensure worker; on fail → remain `RECOVERY_BLOCKED` with
updated reason codes. Stop / emergency-stop from `RECOVERY_BLOCKED` enter
`STOPPING`→`STOPPED` (flatten if safe mark; else `unsafe_unflattened`).

**Rationale**: Clarification “operator may resume same session after gates” vs
stop/new session.

**Alternatives considered**: Reuse `/start` from CONFIGURED only — rejected
(would conflate new session start with recovery resume).

---

## R8 — UI / observability

**Decision**:
- Extend session status panel + history filters for `RECOVERY_BLOCKED`.
- Show `recoveryReason` / gate failure codes; skipped-gap summary when present.
- Emergency stop enabled from `RECOVERY_BLOCKED` and degraded `RUNNING`.
- Layout must remain usable at ~375px (existing Auto Trading patterns; no 4th nav).
- Structured logs: `session_id`, `recovery_outcome`, gate codes; no secrets.

**Rationale**: FR-016, FR-017, SC-006/007.

---

## R9 — Out of scope confirmation

**Decision**: No XT private trading; no RealExecutionAdapter activation; no Real
mode; Simulation Portfolio only for paper; public market retries only as R5;
Backtest semantics unchanged.

**Rationale**: Spec Out of Scope + FR-018/019.

---

## Resolved NEEDS CLARIFICATION

| Item | Resolution |
|------|------------|
| Clarify deferred #4 persistence | R4 |
| Clarify deferred #6 retry bounds | R5 |
| State machine for RECOVERY_BLOCKED | R2 |
| Reconcile gate codes | R3 |
| Resume endpoint | R7 |

No remaining planning NEEDS CLARIFICATION for Phase 1 design.
