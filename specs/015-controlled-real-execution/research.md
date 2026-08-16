# Research: Feature 015 — Controlled Real Execution

**Date**: 2026-08-16  
**Branch**: `015-controlled-real-execution`  
**Sources**: Clarified `spec.md` (Session 2026-08-16 Q1–Q5); Features
012–014/025 baselines; Feature 013 private read client; XT Spot v4
`POST /v4/order`; constitution I–V, VIII–IX, XVII–XVIII, XXXII, XXXIV.

---

## R1 — Session model: same entity, Real mode

**Decision**: Reuse `SimulationSessionRow` / session API / worker with
`mode="real"`. Remove the current hard reject (`real_money_unavailable`) for
valid Real creates. Keep one Strategy → Controller → Risk → Execution pipeline;
branch only at Execution, accounting, Portfolio projection, and recovery.

**Rationale**: Clarification Q1 + FR-001; constitution III (single pipeline).

**Alternatives considered**:
- Separate RealSession table/engine — rejected (second engine).
- Fork pipeline package — rejected (duplication; autonomy later harder).

---

## R2 — Confirmation gate placement

**Decision**: After Controller + Risk **APPROVE** an exposure-increasing Real
BUY, Execution **does not** call RealExecutionAdapter. Persist a
`PendingEntryConfirmation` (or equivalent session columns), expose
`pendingConfirmation` on status, and wait for operator
`POST .../confirm-entry` or `POST .../decline-entry`. Session remains
`RUNNING` (strategy may continue evaluating; no second concurrent pending BUY).
TTL **5 minutes** from creation → discard intent, no XT order, session stays
`RUNNING`. Confirm re-runs final safety/risk/cap checks then submits.

**Rationale**: Clarification Q4 + FR-002/002a/002b; ROADMAP entry flow.

**Alternatives considered**:
- New session state `WAITING_FOR_CONFIRMATION` that stops the worker — rejected
  (spec: keep session running on expiry; TTL discard without stop).
- Confirm inside UI only without server gate — rejected (bypass risk).
- Auto-place with UI toast — rejected (not Controlled Real).

---

## R3 — Reducing exits skip confirmation

**Decision**: TP/SL protective SELLs (025 closed-candle rules), strategy SELLs
that reduce/close the session long, and emergency/STOP flatten (when safe)
call RealExecutionAdapter **without** the entry confirmation gate. Precedence
unchanged: session/emergency → SL → TP → strategy.

**Rationale**: Clarification + FR-003 / FR-009; capital protection favors fast
risk reduction.

**Alternatives considered**:
- Confirm every exit — rejected (unsafe delay).
- Confirm only emergency — rejected (spec: auto protective + reducing).

---

## R4 — Market orders only; submission ≠ fill

**Decision**: RealExecutionAdapter places XT Spot **MARKET** orders only via
signed `POST https://sapi.xt.com/v4/order` with `bizType=SPOT`,
`type=MARKET`, `side=BUY|SELL`. Typical sizing:
- BUY: prefer quote notional (`quoteQty`) bounded by session cash /
  maxPositionSize / 50 USDT cap;
- SELL: base `quantity` = session position qty (full close for MVP one-long).

Adapter returns success **only** when reconcile (GET order / balances) proves
fill (or partial per defined MVP rule — prefer fail closed / wait until
terminal filled or rejected). **Never** treat HTTP 200 place ack alone as a
fill. Limit types rejected at API/adapter (`limit_orders_unavailable`).

Extend `XtPrivateClient` with `place_market_order(...)` (and optional cancel
only if needed for fail-closed cleanup). Keep Feature 013 **public** HTTP
routes read-only (no open place-order REST for arbitrary clients).

**Rationale**: Clarification Q2 + FR-006/006a; XT v4 spot docs / demos.

**Alternatives considered**:
- Limit entries — deferred post-MVP.
- Optimistic fill from place response qty — rejected (invented truth).
- Separate trading HTTP microservice — rejected (complexity).

---

## R5 — Capital cap and Portfolio isolation

**Decision**:
- Real create: `allocatedCapital ≤ 50` USDT (hard), `0 < maxPositionSize ≤
  allocatedCapital`; reject multi-symbol / multi-position config.
- Re-check cap at confirm and immediately before XT entry submit.
- Real sessions **do not** reserve or mutate Simulation Portfolio allocations /
  holdings on create, fill, or close (FR-001a / FR-006 / SC-006).
- Simulation create path unchanged (still Portfolio-aware).

**Rationale**: Clarification Q3 + FR-004; constitution XXXIV for Sim remains;
Real uses XT account as capital truth under session bounds.

**Alternatives considered**:
- Bind Real to Portfolio allocation — rejected for MVP (blurs Sim ledger;
  Portfolio redesign out of scope).
- Soft warning above 50 USDT — rejected (fail closed).

---

## R6 — Real blocked recovery (do not extend 014 auto-resume)

**Decision**: On backend startup, if a `mode=real` session was `RUNNING` /
`STOPPING` (or had in-flight Real orders):
1. Transition to `RECOVERY_BLOCKED` (reuse state enum).
2. Discard **all** pending entry confirmations.
3. Reconcile via Feature 013 (balances, open orders, order status) vs local
   session.
4. **Never** auto-resume Real to `RUNNING`.
5. Operator `Resume` only when reconcile proves safe **and** safety/risk
   re-check passes; else Resume unavailable.
6. Operator Stop/Flatten uses reconciled trustworthy XT state when executable.

Simulation `mode=simulation` keeps Feature 014 conditional auto-recovery
behavior unchanged.

**Rationale**: Clarification Q5 + FR-011.

**Alternatives considered**:
- Reuse 014 auto-resume for Real — rejected explicitly.
- Always force STOPPED on Real restart — weaker (lose explicit Resume path);
  blocked + operator choice preferred.

---

## R7 — Local Real ledger vs FillResult

**Decision**: Keep ExecutionEngine protocol. For Real:
- `FillResult.ok=true` with `fill` only when XT reconcile supplies executable
  fill economics (price, qty, fee if available).
- Intermediate “submitted / pending reconcile” is tracked on session/order
  rows (`real_order_id`, `reconcile_status`), not as a fake FillQuote.
- Pipeline must not apply Simulation accounting helpers from mark/next-open
  for Real fills.

**Rationale**: FR-006; 012 adapter contract stability.

**Alternatives considered**:
- Change protocol to async-only — deferred (wrap poll inside `execute` with
  bounded timeout for MVP).
- Dual ledgers with Sim portfolio mirror — rejected (SC-006).

---

## R8 — UI / API distinctness

**Decision**: Same Auto Trading / session surfaces with unmistakable
`mode: "real"`, labels (“REAL”), pending-confirm panel, blocked-recovery
banner, and history provenance. No new primary nav; no Portfolio redesign.
Confirm/decline actions only for Real pending BUY.

**Rationale**: FR-007 / SC-005; constitution XIII–XIV.

**Alternatives considered**:
- Separate Real app section — rejected (scope / Portfolio redesign risk).

---

## R9 — Testing strategy

**Decision**: Default CI uses fakes for XT place/get. Cover: no XT without
confirm; TTL discard; confirm-time validation fail; market-only reject limit;
auto exit without confirm; cap reject; Portfolio isolation; ack≠fill;
blocked recovery / Resume gate. Optional live smoke behind credentials env.

**Rationale**: FR-010 / SC-001–SC-008.

**Alternatives considered**:
- Require live XT in CI — rejected (non-deterministic / unsafe).

---

## Resolved clarifications

All Technical Context items resolved from Q1–Q5 + existing stack. No remaining
`NEEDS CLARIFICATION`.
