# Quickstart: Feature 019 — Offline UGE search

**Date**: 2026-09-05  
**Goal**: Validate FORGE `uge` + CryptoAutoTrading BNF/fitness on Backtest
train split; freeze phenotype for Backtest UI — without Real money.

See also: [contracts/uge-search-api.md](./contracts/uge-search-api.md),
[data-model.md](./data-model.md), [research.md](./research.md),
[`docs/FORGE_INTEGRATION.md`](../../docs/FORGE_INTEGRATION.md).

---

## Prerequisites

```bash
cd backend
source .venv/bin/activate
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE"
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE/packages/uge"
python -c "from uge import UGEEngine, Grammar; from torque import check; print('ok')"
```

---

## 1. Automated gates (preferred)

```bash
cd backend
source .venv/bin/activate
pytest -q \
  tests/unit/test_uge_search_splits_grammar.py \
  tests/unit/test_uge_search_fitness.py \
  tests/unit/test_uge_search_persist.py \
  tests/integration/test_uge_offline_run.py \
  tests/integration/test_uge_frozen_backtest.py
```

Frontend (Backtest frozen picker):

```bash
cd frontend
npm test -- --run src/__tests__/backtestPhenotypeSelect.test.tsx
```

Expect:

- Chronological split preserves order
- Invalid phenotype → `EvaluationResult(ok=False)`
- Seeded UGE run completes; train fitness matches 016 evaluate
- Same seed → same best phenotype
- `torque_phenotype` Backtest path works
- No Real place imports from `uge_search`

---

## 2. Manual smoke

```bash
cd backend
python - <<'PY'
from app.market_data.models import Candlestick
from app.uge_search import run_uge_search, persist_run_result

def candles(n=80):
    out, px, t = [], 12000, 1_700_000_000_000
    for i in range(n):
        px += 100 if i >= 35 else -80
        s = f"{px/100:.2f}"
        out.append(Candlestick(openTime=t+i*3_600_000, open=s, high=s, low=s, close=s))
    return out

r = run_uge_search(candles(), seed=7, population_size=6, n_generations=2)
print(r.status, r.best_phenotype, r.train_fitness, r.validation_fitness)
if r.best_phenotype:
    print("saved", persist_run_result(r))
PY
```

Backtest UI: select strategy **Torque phenotype**, paste phenotype or use
**Load frozen UGE phenotype** if artifacts exist under `backend/data/uge_runs/`.

Grammar knobs: edit discrete alternatives in
`backend/app/uge_search/grammars/trading_mvp.bnf`; `max_depth` / pop / ngen via
`run_uge_search(...)`.

---

## 3. Safety checklist

| Check | Expected |
|-------|----------|
| FORGE/UGE vendored in repo | Absent |
| Selection uses test split | Never |
| Real / Kraken place from fitness | None |
| Auto Simulation/Real from UGE | None |

---

## 4. Out of scope

- Strategy Comparison multi-run
- Experiment lab UI (020)
- Controlled Real (015)
