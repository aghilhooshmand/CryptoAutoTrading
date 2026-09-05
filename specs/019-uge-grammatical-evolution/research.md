# Research: Feature 019 — UGE search (FORGE)

**Date**: 2026-09-05  
**FORGE path**: `/home/aghil/Documents/my document/limerick/projects/FORGE`

## R1 — Dependency mode

**Decision**: Editable install of FORGE `packages/uge` into the backend venv
(`pip install -e …/FORGE/packages/uge`). Documented in
`docs/FORGE_INTEGRATION.md`. No vendoring. Feature 016 already uses `torque`
from FORGE root; 019 adds/uses `uge`.

**Rationale**: Constitution XXXVI — call FORGE UGE; do not reimplement GE.

**Alternatives considered**: Homegrown GE loop — rejected. Vendor `uge` source —
rejected.

## R2 — Public FORGE API consumed in 019

Verified locally:

```python
from uge import (
    UGEEngine, Grammar, EvaluationResult, Fitness,
    EngineRunConfig, InitConfig, SelectionConfig,
    RankingProjection, run, RunOutcome,
)
# Individual.mapping.phenotype : str
# EvaluationResult(ok=True, fitness=Fitness([v], ["maximise"|"minimise"]))
# engine.register("evaluate", callable).run(grammar=..., pop=..., ngen=..., seed=...)
# or run(EngineRunConfig(...)) → RunOutcome(best_individual=...)
```

Expression-proof example pattern (FORGE `examples/expression_proof`) is the
template: custom evaluator + BNF + `run(cfg)`.

**Decision**: Prefer `UGEEngine` facade for app code (matches FORGE docs /
operator mental model); tests MAY use `run(EngineRunConfig)` equivalently.

## R3 — What we do not import

- FORGE `force` / sklearn catalogue
- Copy of UGE or Torque trees into this repo
- `RealExecutionAdapter` / Kraken place from fitness or runner

## R4 — Fitness definition (MVP)

**Decision** (spec Session 2026-09-05 Option B + FR-005):

**Default**:
```text
fitness = float(netProfit - buyAndHoldNetProfit)
Fitness([fitness], ["maximise"])
```

Operator MAY select an alternate **single** scalar via run config `fitnessId`
from a documented allow-list (e.g. `net_minus_bh` default, `net_profit`).
Multi-objective deferred to Feature 022.

Values come from Feature 016 `evaluate_phenotype` metrics (fee/slippage aware).
Invalid Torque form / bind / Backtest failure → `EvaluationResult(ok=False)`.

**Alternatives considered**: Sharpe-only default — deferred. Locked-only
formula (clarify Option A) — rejected for operator flexibility.

## R5 — BNF / grammar (MVP)

**Decision** (Session 2026-09-05 Option A): Checked-in `trading_mvp.bnf` with
**discrete** parameter alternatives only (operator-editable list). Continuous
min–max generation is out of MVP (search space too large).

Phenotypes are Torque source strings Feature 016 can `check`/`bind`, including:

- Leaves: `rsi`, `macd`, `dual_ema` with discrete ParamDef-aligned keywords
  (e.g. `period=7|10|14|21`).
- Composition: `and(…)`, `or(…)`, `vote(…)` with ≥2 leaf children.
- Max depth via UGE `max_depth` + grammar structure (compose-of-leaves MVP).

## R6 — Train / validation / test (021 minimum)

**Decision**: Chronological split of the candle snapshot by count ratios
(default **60% / 20% / 20%**, configurable). Indices are contiguous prefixes
of sorted `openTime`.

| Split | Use |
|-------|-----|
| train | Fitness during UGE selection / evolution |
| validation | Report best individual's fitness after search (not used to pick among population during evolution) |
| test | Held out; optional final report only after phenotype frozen; **never** used for selection |

**Rationale**: Constitution XXXVIII / FR-007. Not full walk-forward (021 later).

## R7 — Reproducibility

**Decision**: Fix `rng_seed`, grammar text/path, candle snapshot, capital/fees,
pop/ngen/max_depth, and split ratios. Same inputs → same best phenotype and
fitness sequence (FORGE SC pattern from expression_proof). Document any
tolerated float noise as exact Decimal→float conversion from metrics strings.

## R8 — Persistence + Backtest UI (US3)

**Decision** (Session 2026-09-05 Option B + compare Option A):

1. Write JSON artifact after a run (phenotype, train/val fitness, seed,
   grammarId, fitnessId, split ratios).
2. Expose frozen phenotype as a **Backtest UI–selectable** input (e.g. strategy
   id `torque_phenotype` with `phenotype` param, and/or list saved artifacts).
3. Strategy Comparison multi-run wiring is **not** required for 019 DONE.
4. MUST NOT auto-start Simulation or Real from UGE results.

Re-evaluate via Feature 016 / Backtest path without a live UGE process.

## R9 — Run scale for tests vs operator smoke

**Decision**: Automated tests use tiny `population_size` / `n_generations`
(e.g. 8×3) on fixture candles. Operator smoke MAY use larger values; not a
DONE gate.

## R10 — UI / HTTP

**Decision**: No operator UI in 019 (020). Optional CLI/module entry
`run_uge_search(...)` is the DONE surface. HTTP optional and non-blocking
(same stance as 016).

## Resolved unknowns

| Topic | Resolution |
|-------|------------|
| UGE API | R2 |
| Fitness | R4 |
| BNF | R5 |
| Leakage / splits | R6 |
| Replay | R7 |
| Frozen phenotype | R8 |
| Real money | Out of scope |
