# Quickstart: Feature 016 — Torque bind / Backtest evaluate

**Date**: 2026-09-04  
**Goal**: Validate FORGE `torque.check` + CryptoAutoTrading bind/evaluate on
Simulation/Backtest path without Real money.

See also: [contracts/torque-bind-api.md](./contracts/torque-bind-api.md),
[data-model.md](./data-model.md), [research.md](./research.md),
[`docs/FORGE_INTEGRATION.md`](../../docs/FORGE_INTEGRATION.md).

---

## Prerequisites

- Branch / feature dir: `specs/016-torque-trading-program`
- Backend venv with editable FORGE:

```bash
cd backend
source .venv/bin/activate
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE"
# optional for later 019:
# pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE/packages/uge"
python -c "from torque import check; assert check('rsi(period=14)').ok"
```

---

## 1. Automated gates (preferred)

After implement:

```bash
cd backend
source .venv/bin/activate
pytest -q \
  tests/unit/test_torque_bind_catalogue.py \
  tests/unit/test_torque_bind_check_bind.py \
  tests/unit/test_torque_bind_evaluate.py \
  tests/integration/test_torque_backtest_evaluate.py
```

Expect:

- Invalid Torque text → `invalid_torque_form` (no Backtest)
- Unknown leaf → `unknown_torque_leaf`
- `and(rsi(...), macd(...))` / `and(dual_ema(...), rsi(...))` binds and evaluates
- Same phenotype + fixture candles → identical `netProfit` / `netPnl`
- Composition changes outcomes vs single leaf (SC-002)
- No RealExecutionAdapter place path imported from `app.torque_bind`

---

## 2. Manual smoke (after Python API exists)

```bash
cd backend
python - <<'PY'
from torque import check
print("forge", check("vote(rsi(period=14), dual_ema(fastPeriod=9, slowPeriod=21))").ok)
# after implement:
# from app.torque_bind import evaluate_phenotype
# ...
PY
```

---

## 3. Safety checklist

| Check | Expected |
|-------|----------|
| FORGE source in this repo | Absent |
| Real / Kraken place from evaluate | None |
| Simulation Portfolio | Unchanged by evaluate (Backtest isolation) |
| Public `/market/*` | Still works without Torque |

---

## 4. Out of scope for this quickstart

- UGE search loop (Feature 019)
- Controlled Real (015)
- Live exchange credentials
