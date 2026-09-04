# Research: Feature 016 — Torque binding (FORGE)

**Date**: 2026-09-04  
**FORGE path**: `/home/aghil/Documents/my document/limerick/projects/FORGE`

## R1 — Dependency mode

**Decision**: Editable pip install of FORGE root (`torque` language API) into
the backend venv. Documented in `docs/FORGE_INTEGRATION.md`. No vendoring.
`packages/uge` may already be installed for later 019 but is **not** required
for 016 DONE.

**Rationale**: Operator lock — call FORGE, never copy. Verified
`from torque import check` in this project's venv.

**Alternatives considered**: Vendor `src/torque` — rejected. Rewrite a mini
parser — rejected (constitution XXXV).

## R2 — Public FORGE API consumed in 016

```python
from torque import check  # CheckResult: .ok, .program, .error
# Program.root: Instruction(name, positional, keywords)
# Literal / nested Instruction
```

**Decision**: Phenotype = Torque source string. Binding walks `Program` after
`check(...).ok`.

## R3 — What we do not import

- `force` / sklearn catalogue
- Legacy `docs/sources/legacy-torque/`
- Any copy of FORGE trees into this repo
- `RealExecutionAdapter` / Kraken place from bind/evaluate

## R4 — Heavy transitive deps note

Installing FORGE root currently pulls pandas/sklearn because FORCE shares the
distribution named `torque`. Acceptable for local MVP; still only **call**
`torque` language APIs.

## R5 — Composition semantics (AND / OR / vote)

**Decision** (agreement-style on `StrategySignal.side`):

| Op | Torque instruction name(s) | Rule |
|----|------------------------------|------|
| AND | `and` (alias `And`) | BUY only if all children BUY; SELL only if all SELL; else HOLD |
| OR | `or` (alias `Or`) | BUY if any BUY and no SELL; SELL if any SELL and no BUY; conflict → HOLD; else HOLD |
| vote | `vote` | Majority of non-HOLD sides; tie / empty → HOLD |

Children are nested instructions (strategies or further composition). Verified
Torque parses e.g. `and(rsi(period=14), macd(fastPeriod=12, slowPeriod=26, signalPeriod=9))`.

**Rationale**: Matches operator intent (“both say sell → sell”). Not arithmetic
mean of indicator series.

**Alternatives considered**: AVG as mean of RSI values — rejected unless later
spec defines it. Weighted vote — defer.

## R6 — Leaf mapping

**Decision**: Instruction name (case-sensitive as parsed; bind resolves
case-insensitively to registry id) MUST match an existing strategy id
(`rsi`, `macd`, `dual_ema`, …). Keywords MUST use existing ParamDef names
(`period`, `fastPeriod`, `slowPeriod`, `signalPeriod`, …). Positional args
for leaves are out of MVP (keywords only) to avoid ambiguous ordering.

MVP leaf set (minimum for SC-001): `rsi`, `macd`, `dual_ema`. Other registry
strategies MAY be allowed if params map cleanly.

**Param metadata (FR-002)**: Catalogue (or thin helper) MUST expose each MVP
leaf’s ParamDef names, types, and bounds from the strategy registry so bind
validation and Feature 019 BNF can reuse them without re-declaring schemas.
016 does **not** author the UGE BNF file.

## R7 — Evaluate surface

**Decision**: Python API first:

```text
evaluate_phenotype(source: str, *, candles, capital, fees, …) -> TorqueEvaluateResult
```

Internally: `check` → bind → `Strategy` → Feature 004 `run_engine` via
`run_bound_backtest` (or equivalent) → metrics. Public `evaluate_phenotype`
wraps that wire with the success/failure envelope in contracts/torque-bind-api.md.

Optional thin HTTP `POST /torque/evaluate` for smoke — **not required for
016 DONE** when unit/integration tests cover the Python API. Implement HTTP
only if operator smoke is worth the extra files; do not block DONE on routes.

**Rationale**: Feature 019 UGE will register an evaluate callable in-process;
HTTP is optional sugar.

**US2 vs US3 split**: US2 owns Backtest wiring (`run_bound_backtest` or
equivalent internal helper calling `run_engine` with a bound `Strategy`).
US3 owns the public `evaluate_phenotype` envelope (`ok` / `metrics` /
`effectiveLeaves` / failure codes) wrapping that helper. US2 integration
tests MUST call the Backtest wire (or bind + `run_engine`), not require the
full US3 contract shape.

## R8 — Fail-closed codes

**Decision**: Stable codes for bind/evaluate failures (API or raised domain
errors): `invalid_torque_form`, `unknown_torque_leaf`, `invalid_torque_params`,
`invalid_composition`, `evaluate_failed`. Never invent fills on failure.

## R9 — Simulation vs Backtest for MVP

**Decision**: **Backtest fixtures** are the DONE gate (deterministic SC-003).
Simulation path MAY be wired as a follow-up inside 016 if cheap; not blocking.

## Resolved unknowns

| Topic | Resolution |
|-------|------------|
| FORGE install | R1 + FORGE_INTEGRATION.md |
| Phenotype syntax | R2, R5, R6 |
| Composition meaning | R5 |
| Evaluate shape | R7 |
| Real money | Out of scope (spec lock) |
