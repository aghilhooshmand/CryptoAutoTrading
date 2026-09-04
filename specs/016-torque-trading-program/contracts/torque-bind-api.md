# Contract: Torque bind / evaluate (Feature 016)

**Feature**: `016-torque-trading-program`  
**Date**: 2026-09-04  
**Depends on**: FORGE `torque` (editable); Feature 004 Backtest engine;
Feature 005/006 strategy registry  
**Non-goals**: UGE loop; Real orders; FORGE source in this repo

## Phenotype examples (normative for tests)

```text
rsi(period=14, oversold=30, overbought=70)

and(
  rsi(period=14),
  macd(fastPeriod=12, slowPeriod=26, signalPeriod=9)
)

vote(
  dual_ema(fastPeriod=9, slowPeriod=21),
  rsi(period=14)
)
```

Keyword names MUST match registry ParamDef names.

## Python API (required)

```python
from app.torque_bind import check_phenotype, bind_phenotype, evaluate_phenotype

result = check_phenotype(source)   # wraps torque.check; domain errors
strategy = bind_phenotype(source)  # Strategy protocol; raises on failure
out = evaluate_phenotype(source, candles=..., starting_capital=..., ...)
# Internally evaluate_phenotype uses run_bound_backtest (US2) + envelope (US3)
```

### `evaluate_phenotype` success shape (logical JSON)

```json
{
  "ok": true,
  "phenotype": "and(rsi(period=14), macd(fastPeriod=12, slowPeriod=26, signalPeriod=9))",
  "metrics": {
    "netProfit": "12.34",
    "totalReturn": "0.0123",
    "tradeCount": 4,
    "buyAndHoldNetProfit": "10.00"
  },
  "effectiveLeaves": [
    {"strategyId": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
    {"strategyId": "macd", "params": {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}}
  ]
}
```

### Failure envelope

```json
{
  "ok": false,
  "error": {
    "code": "invalid_torque_form",
    "message": "..."
  }
}
```

Stable codes: `invalid_torque_form`, `unknown_torque_leaf`,
`invalid_torque_params`, `invalid_composition`, `evaluate_failed`.

## Optional HTTP (smoke only)

If implemented:

| Method | Path | Body |
|--------|------|------|
| POST | `/torque/check` | `{ "phenotype": "..." }` |
| POST | `/torque/evaluate` | phenotype + backtest knobs or fixture id |

Same error codes. No credentials. No Real mode fields.

## Composition rules (normative)

See research.md R5. Combinators only combine `BUY`/`SELL`/`HOLD` sides —
they do not invent prices.

## Import rules

- `app.torque_bind` MAY import `torque` (FORGE).
- `app.torque_bind` MUST NOT import FORGE `force`.
- Strategy/Controller/Risk modules MUST NOT import FORGE packages in 016
  (bind adapter is the boundary).
