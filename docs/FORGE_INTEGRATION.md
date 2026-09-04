# FORGE dependency (Torque + UGE)

CryptoAutoTrading **calls** FORGE packages; it does **not** copy FORGE source.

## Local path (this machine)

```text
/home/aghil/Documents/my document/limerick/projects/FORGE
```

## Install into the backend venv (editable)

From `backend/` with `.venv` active:

```bash
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE"
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE/packages/uge"
```

Optional plots for UGE:

```bash
pip install -e "/home/aghil/Documents/my document/limerick/projects/FORGE/packages/uge[viz]"
```

## Imports we use

```python
from torque import check
from uge import UGEEngine, Grammar, EvaluationResult, Fitness
```

- **Feature 016** — `torque.check` + this project's strategy binding / Backtest evaluate  
- **Feature 019** — `UGEEngine` + BNF/fitness owned here  

Do **not** import `force` for trading leaves (FORCE's sklearn catalogue is a different app).

## Notes

- Root FORGE install currently publishes the PyPI-style name `torque` and may
  pull ML extras (pandas/sklearn) because FORCE lives in the same distribution.
  We still only **call** `torque` language APIs for trading.
- CI / other machines: set the same editable paths (or a future published
  package URL) — never vendor `src/torque` or `packages/uge` into this repo.
