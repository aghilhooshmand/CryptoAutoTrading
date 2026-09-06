# Quickstart: Evolution Experiments (Feature 020)

**Feature**: `020-evolution-experiments`  
**Date**: 2026-09-06

## Prerequisites

- Backend venv with FORGE `uge` editable (`docs/FORGE_INTEGRATION.md`).
- API `:8000`, UI `:5173`.

## Automated gates

```bash
cd backend && source .venv/bin/activate
pytest -q \
  tests/unit/test_uge_experiment_store_runner.py \
  tests/unit/test_uge_grammar_builder.py \
  tests/unit/test_uge_frozen_catalogue.py \
  tests/integration/test_uge_experiment_stream.py \
  tests/integration/test_frozen_catalogue_backtest.py \
  tests/contract/test_uge_experiments_api.py
```

```bash
cd frontend && npm test -- --run \
  src/__tests__/evolutionConfig.test.tsx \
  src/__tests__/evolutionFreeze.test.tsx
```

## Manual UI (020a–c)

1. Open **Auto Trading → Evolution**.
2. Set pop/ngen/seed, candle window, optional leaf/op filters → **Start evolution**.
3. Confirm generations table + chart update while status is `running`.
4. After terminal status, freeze with a unique display name.
5. In **Backtest** / **Simulation**, select the new `uge_frozen_…` strategy.
6. Confirm Evolution has no Real place/confirm controls.

## Notes

- One experiment at a time; second start → 409.
- Cancel applies at the next generation boundary.
- Lab never auto-starts Real.
