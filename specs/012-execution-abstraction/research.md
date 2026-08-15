# Research: Execution Abstraction (012)

**Date**: 2026-08-15  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Phase 0 decisions. All plan Technical Context items resolved; no remaining
NEEDS CLARIFICATION.

---

## R1 — Package location for the shared contract

**Decision**: Create `backend/app/execution/` as the mode-neutral home for
`ExecutionIntent`, `FillResult`, `ExecutionEngine`, shared economics, and the
three adapters (Historical, Simulation, Real).

**Rationale**: Constitution XXXII and the roadmap diagram place execution
outside Simulation-only namespaces. Putting the contract under
`app.simulation.execution` would keep Historical and Real conceptually owned
by Simulation.

**Alternatives considered**:
- Keep everything under `app.simulation.execution` and have Backtest import it
  — rejected (wrong ownership; invites Portfolio coupling).
- Duplicate Protocol in both packages — rejected (second contract).

---

## R2 — Consolidation depth (clarification Option B)

**Decision**: Extract shared **fill economics + rejection sizing** into
`economics.py` (buy/sell from a fully populated `ExecutionIntent`). Adapters
are thin: validate mode-agnostic side rules via shared core, return
`FillResult`. **Do not** merge into shared core: next-open vs live mark
selection, journal persistence, flatten orchestration, or Portfolio
holdings/reserved updates.

**Rationale**: Matches clarify lock; today’s
`SimulationExecutionEngine` and `HistoricalExecutionAdapter` already share
identical buy/sell math with different method shapes.

**Alternatives considered**:
- Façade-only (A) — rejected; leaves duplicate economics and weak Real hook.
- Aggressive merge including flatten/journal (C) — rejected; high behavior
  risk without proven equivalence.

---

## R3 — Unify result types and Historical API shape

**Decision**: One `FillResult` dataclass for all modes (replace
`HistoricalFillResult` as a distinct type). `HistoricalExecutionAdapter`
implements `ExecutionEngine.execute(intent)`. Keep thin `buy(...)` / `sell(...)`
wrappers that build `ExecutionIntent` and call `execute`, so
`backtest/engine.py` `_flatten` and strategy-fill call sites can migrate
incrementally with minimal diff.

**Rationale**: Spec requires production strategy fills through the shared
contract; wrappers preserve readability for flatten helpers without a second
result type.

**Alternatives considered**:
- Force all call sites to `execute` only in one PR — acceptable later but
  larger churn; wrappers first reduce regression risk.
- Keep `HistoricalFillResult` forever — rejected (forked contract).

---

## R4 — Who supplies `reference_price`

**Decision**: Callers (Simulation pipeline / session forced-close; Backtest
engine next-open or flatten reference) compute `reference_price` and pass it
on the intent. Adapters do **not** fetch candles or marks.

**Rationale**: Spec FR-006/FR-007 — timing and price source are mode-owned.
Keeps Historical deterministic and Simulation on its safe-mark path.

**Alternatives considered**:
- Adapter fetches next candle / live mark — rejected (embeds mode policy in
  shared layer; harder to test; violates clarify lock).

---

## R5 — Real stub behavior

**Decision**: `RealExecutionAdapter.execute` always returns
`FillResult(ok=False, reason_code="real_execution_unavailable", ...)` with
`fill`/`qty` null. No exchange I/O; no Portfolio/ledger mutation (adapter has
no side-effect hooks). Not registered in operator UI or session create APIs.

**Rationale**: Clarify Option A reachability + Option A failure shape.

**Alternatives considered**:
- Exception-only failure — rejected (inconsistent with fill-failure contract).
- Operator-visible Real mode that always fails — rejected (UX hazard).

---

## R6 — Comparison path

**Decision**: No Comparison-specific execution work. Feature 007 already
orchestrates legs via Feature 004 `run_engine`, which uses
`HistoricalExecutionAdapter`. After 012, that remains the sole Historical
path; verify with existing Comparison/Backtest regressions if present.

**Rationale**: Clarify Option A — reuse same Historical adapter/path;
Comparison orchestration unchanged.

**Alternatives considered**:
- Direct Comparison→economics calls — rejected (third fork).
- Defer Comparison verification entirely — weak; at least confirm import path
  still resolves through shared Historical adapter.

---

## R7 — Compatibility shims

**Decision**: Keep import compatibility for
`app.simulation.execution.port` and `app.backtest.execution` via
**re-export-only** shims from `app.execution` (zero local fill math bodies).
Prefer updating primary call sites to `app.execution` where touched.
Optional alias `HistoricalFillResult = FillResult` during migration.

**Rationale**: Reduces blast radius while forbidding a second implementation
behind old imports (analyze I1).

**Alternatives considered**:
- Big-bang import rewrite — higher conflict risk with little benefit.
- “Thin delegates” that still contain fill bodies — rejected (second engine).
- Leave permanently duplicated implementations behind shims — rejected.

---

## R7b — Call-site inventory location

**Decision**: Document fill call sites in
`specs/012-execution-abstraction/call-sites.md`, not in
`backend/app/execution/__init__.py` comments.

**Rationale**: Analyze I8 — package `__init__` comments go stale; Feature docs
are the durable inventory.

**Alternatives considered**:
- Comment block in `__init__.py` — rejected (stale risk).

---

## R8 — Behavior-preservation gate

**Decision**: DONE requires existing Simulation and Backtest fill/pipeline
suites green with **unchanged expectations**, plus new unit tests that
dual-oracle shared economics against **both** current engines
field-by-field (qty, notional, fee, slippage_cost, cash_delta, dust, sizing,
reject codes) before deleting old bodies, plus Real stub tests.

**Rationale**: Spec SC-001/SC-002/FR-017; analyze I3.

**Alternatives considered**:
- Snapshot-only new tests without running old suites — rejected (insufficient).
- “Looks identical” without field-level oracle — rejected.
---

## R9 — Frontend / HTTP

**Decision**: No REST contract changes; no frontend work.

**Rationale**: Architectural backend feature; Real not operator-selectable.

**Alternatives considered**:
- Document a public “execution mode” API — out of scope until 013+.
