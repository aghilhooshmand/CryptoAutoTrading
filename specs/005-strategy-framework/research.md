# Research: Strategy Framework and Selection

**Feature**: `005-strategy-framework`  
**Date**: 2026-08-11

All Technical Context items resolved; no remaining NEEDS CLARIFICATION.

---

## Decision 1: Shared `app/strategy` package (not simulation-owned)

**Decision**: Introduce `backend/app/strategy/` as the single home for the
strategy protocol, registry, parameter validation, and Dual EMA
implementation. Both `simulation` and `backtest` import from here.

**Rationale**: FR-008 requires the same implementation for Simulation and
Backtest. Keeping Dual EMA under `simulation.strategy` invites accidental
forks (Feature 004 already hard-imports Dual EMA). A shared package makes
the boundary obvious and matches constitution III.

**Alternatives considered**:
- Keep files under `simulation/strategy` and import from backtest — works but
  implies simulation ownership and confuses future non-sim strategies.
- Duplicate Dual EMA in backtest — forbidden by FR-008 / constitution X–XI.

---

## Decision 2: Registry resolve with canonical id + alias map

**Decision**: Registry maps canonical ids → strategy entry (factory,
param schema, display name). Separate alias map: `dual_ema_9_21` → `dual_ema`.
`resolve(raw_id)` returns `(canonical_id, entry)`. Create paths call
`validate_and_materialize(raw_id, params|None) → (canonical_id, effective_params)`.

**Rationale**: Matches clarifications (B): Dual EMA is the strategy; 9/21 is
configuration; legacy id remains accepted without being the stored identity.

**Alternatives considered**:
- Keep storing `dual_ema_9_21` forever — contradicts “periods are config.”
- Reject alias immediately — breaks existing clients/rows unnecessarily.

---

## Decision 3: Parameters as JSON object; Dual EMA `fastPeriod` / `slowPeriod`

**Decision**: Persist effective parameters as JSON text column
`strategy_params` on simulation sessions and backtest runs, e.g.
`{"fastPeriod": 9, "slowPeriod": 21}`. API field name: `strategyParams`
(camelCase). Dual EMA schema: integers `fastPeriod` (default 9),
`slowPeriod` (default 21); require `fastPeriod >= 1`, `slowPeriod >= 2`,
`fastPeriod < slowPeriod`.

**Rationale**: Flexible for future strategies without schema migrations per
param; Decimal-safe by storing ints for periods. Effective params always
persisted so inspect/restart shows what actually ran.

**Alternatives considered**:
- Separate DB columns per Dual EMA period — not extensible.
- Store only non-default overrides — complicates inspect and continuity tests.

---

## Decision 4: `strategyId` required; no server-side default to Dual EMA

**Decision**: Create simulation/backtest bodies **must** include `strategyId`.
Omission → `400` / `invalid_config` (or `unknown_strategy` as appropriate).
UI pre-fills `dual_ema`. Breaking change vs Feature 003 contract default
`dual_ema_9_21` — documented in contracts and quickstart.

**Rationale**: Clarification Option A; SC-002.

**Alternatives considered**:
- Server default to Dual EMA when omitted — rejected in clarify.

---

## Decision 5: Strategy factory per session/run (immutable params)

**Decision**: On create, materialize params once. Pipeline/engine constructs
`DualEmaCrossoverStrategy(fast=..., slow=...)` (or registry factory) from
persisted effective params. No mid-run mutation.

**Rationale**: Selection fixed at create; determinism; matches current
engine pattern of constructing strategy once per run.

**Alternatives considered**:
- Re-read mutable config each candle — out of scope / unsafe.

---

## Decision 6: Generalize signal diagnostics lightly

**Decision**: Keep `StrategySignal` with `side`, `candle_open_time`,
`reason_code`, and optional indicator fields used by Dual EMA
(`fast_ema`, `slow_ema` as optional Decimals). Do not require a generic
diagnostics map in v1. Non-Dual-EMA strategies may leave indicator fields
null.

**Rationale**: Minimal migration cost for journals/UI that already show EMA
values; FR-001 only mandates BUY/SELL/HOLD.

**Alternatives considered**:
- Force `diagnostics: dict[str, str]` only — larger churn for Feature 003
  journals without product need in v1.

---

## Decision 7: Insufficient history and warm-up scale with `S`

**Decision**: Dual EMA exposes `min_history_candles(effective_params) -> S`
(slow period). Backtest service uses that for `insufficient_history` instead
of hard-coded `21`. Strategy warm-up remains `len(closes) < S + 1` → HOLD.
Default `S=21` preserves Feature 004 gate.

**Rationale**: Clarification Option B / FR-005b.

**Alternatives considered**:
- Both gates `S+1` — stricter than today’s default 21-candle accept.
- Both gates `S` for warm-up — would change crossover semantics vs current code.

---

## Decision 8: `GET /strategies` for UI schema

**Decision**: Add `GET /strategies` returning registered strategies with
canonical id, display name, aliases (optional), and parameter definitions
(name, type, default, minimum/maximum, label). Cross-field rules are exposed
as strategy-level `constraints` with an operator-facing `message` and optional
`fields` list — e.g. Dual EMA: “Fast period must be less than slow period.”
No generic expression/rule engine in Feature 005; UI displays the message;
server always re-validates on create.

**Rationale**: FR-013; frontend can render min/max easily and show one clear
cross-field message without inventing a rules DSL.

**Alternatives considered**:
- Hard-code Dual EMA fields in UI only — fights the registry goal.
- Generic CEL/JSON-Logic rule engine — unjustified complexity (constitution X).
- OpenAPI-only codegen — overkill for local operator app.

---

## Decision 9: Legacy / unknown id lifecycle

**Decision**:
- **READ** existing row: allowed for inspection (alias may normalize to
  `dual_ema`; unknown ids returned as-stored).
- **START / RESUME** execution: only registry-known canonical ids or
  documented aliases; **unknown stored ids are forbidden** (fail safe — do
  not evaluate).
- **NEW create**: unknown ids forbidden; alias `dual_ema_9_21` allowed and
  persisted as canonical `dual_ema`.
No one-shot DB rewrite for legacy `dual_ema_9_21` rows (lazy normalize on
read).

**Rationale**: Inspection must not become an execution path after restart;
matches fail-safe constitution VIII.

**Alternatives considered**:
- Eager SQL UPDATE all rows — unnecessary for single-operator local DB.
- Allow START on unknown id “as no-op” — still unsafe / ambiguous.
---

## Decision 10: Tests for behavioral continuity

**Decision**: Fixture-based unit test: Dual EMA with defaults 9/21 produces
identical signal sequence to a frozen snapshot of pre-migration Dual EMA
behavior on a fixed close series. Separate test: non-default periods change
signals. Contract tests: omit id → 400; alias → 201/created with
`strategyId: "dual_ema"`; invalid periods → 400.

**Rationale**: SC-003, SC-003a, SC-007, FR-009.

---

## Summary

| Topic | Choice |
|-------|--------|
| Package | `backend/app/strategy/` shared |
| Identity | `dual_ema` + alias `dual_ema_9_21` |
| Params | JSON `strategyParams`; Dual EMA fast/slow ints |
| Create | `strategyId` required |
| History | insufficient `< S`; warm-up `< S+1` |
| UI | `GET /strategies` + shared form fields |
| Legacy rows | Lazy normalize on read |
