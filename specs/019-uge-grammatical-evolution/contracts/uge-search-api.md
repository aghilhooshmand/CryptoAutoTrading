# Contract: UGE search (Feature 019)

**Feature**: `019-uge-grammatical-evolution`  
**Date**: 2026-09-05  
**Depends on**: FORGE `uge` (editable); Feature 016 `evaluate_phenotype`;
Feature 004 Backtest (via 016); Feature 021-min chronological split  
**Non-goals**: Experiment UI (020); multi-objective (022); Real orders; vendoring FORGE

## Python API (required)

```python
from app.uge_search import (
    chronological_split,
    load_trading_mvp_grammar,
    make_backtest_evaluator,
    run_uge_search,
    persist_run_result,
    load_frozen_phenotype,
)

split = chronological_split(candles, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
grammar = load_trading_mvp_grammar()
outcome = run_uge_search(
    candles=candles,  # full snapshot; runner applies split internally
    seed=7,
    population_size=8,
    n_generations=3,
    starting_capital="1000",
)
# outcome.best_phenotype: str | None
# outcome.train_fitness: float | None
# outcome.validation_fitness: float | None
```

### Evaluator contract (UGE)

Callable signature compatible with FORGE:

```python
def evaluate(individual, context=None) -> EvaluationResult: ...
```

- Invalid mapping → `EvaluationResult(ok=False)`
- 016 evaluate `ok=False` → `EvaluationResult(ok=False)`
- Success → `EvaluationResult(ok=True, fitness=Fitness([net - bh], ["maximise"]))`
  where `net` / `bh` are floats from metric decimal strings

### Frozen artifact (JSON)

```json
{
  "phenotype": "and(rsi(period=14), dual_ema(fastPeriod=9, slowPeriod=21))",
  "trainFitness": 12.34,
  "validationFitness": 8.0,
  "fitnessId": "net_minus_bh",
  "seed": 7,
  "grammarId": "trading_mvp",
  "split": {"trainRatio": 0.6, "valRatio": 0.2, "testRatio": 0.2}
}
```

`load_frozen_phenotype(path)` returns the phenotype string. Backtest UI MUST be
able to select a frozen artifact (or paste phenotype via `torque_phenotype`
strategy) and run Feature 004 without a live UGE process. Strategy Comparison
multi-run is not required for 019 DONE.

## Grammar obligations

MVP BNF MUST be able to generate:

- At least two distinct leaf strategy forms with parameter alternatives
- At least one composition op (`and` / `or` / `vote`) over leaves

Phenotypes MUST be valid Torque source for Feature 016 (keywords = ParamDef names).

## Import rules

- `app.uge_search` MAY import `uge` (FORGE) and `app.torque_bind`
- `app.uge_search` MUST NOT import FORGE `force` or Real place paths
- Strategy / Controller / Risk MUST NOT import `uge`
- Fitness MUST NOT call exchange private trading APIs

## HTTP / CLI

| Surface | Required for 019 DONE? |
|---------|-------------------------|
| Python `run_uge_search` | **Yes** (primary search entry; FR-010) |
| `GET` list / load frozen artifacts (for Backtest UI) | **Yes** when UI loads artifacts from disk (FR-009) |
| `POST /uge/run` or CLI to start evolution | Optional smoke — not required if pytest covers `run_uge_search` |

Fitness allow-list MVP ids: `net_minus_bh` (default), `net_profit`.
