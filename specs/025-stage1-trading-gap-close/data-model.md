# Data Model: Feature 025 — Stage-1 Trading Gap-Close

**Date**: 2026-08-16  
**Branch**: `025-stage1-trading-gap-close`

---

## 1. Run configuration (percentages)

Stored on Simulation session create / Backtest run config / optional operator
defaults.

| Field | Type | Rules |
|-------|------|-------|
| `take_profit_percent` | nullable decimal string | Omit/null = disabled; if set MUST be `> 0` |
| `stop_loss_percent` | nullable decimal string | Omit/null = disabled; if set MUST be `> 0` and `< 1` for long (cannot wipe below zero entry) |

**Where stored:**

| Surface | Percent columns | Absolute / entry-bar columns |
|---------|-----------------|------------------------------|
| `SimulationSessionRow` | yes | yes (`take_profit_price`, `stop_loss_price`, `entry_fill_candle_open_time`) |
| `BacktestRunRow` | yes (run config) | no — engine state holds derived levels for the in-memory run |
| `OperatorDefaultsRow` | optional yes | no |

Interpretation (long):

```text
take_profit_price = entry_fill_price * (1 + take_profit_percent)
stop_loss_price   = entry_fill_price * (1 - stop_loss_percent)
```

Invalid combinations rejected at create/start (`invalid_config`), fail closed.

**Immutability while long**: percentages for an open position are not updated
(Q6). Changing defaults only affects future creates / future entries after flat.

---

## 2. Position protective state (while long)

On successful BUY fill, derive and persist:

| Field | Type | Lifecycle |
|-------|------|-----------|
| `entry_fill_price` | decimal string | Set on BUY; clear on flat (may already exist on session) |
| `entry_fill_candle_open_time` | int epoch ms | Set on BUY; clear on flat — marks entry-bar skip |
| `take_profit_price` | nullable decimal string | Set if TP% configured; else null |
| `stop_loss_price` | nullable decimal string | Set if SL% configured; else null |

On any closing fill (TP, SL, strategy, forced/session): clear absolute TP/SL and
entry candle cursor (and existing entry fields per current SELL path).

---

## 3. Exit reason

Extend operator-visible stop/exit reason vocabulary with stable codes:

| Code | Meaning |
|------|---------|
| `take_profit` | Protective TP triggered |
| `stop_loss` | Protective SL triggered |
| (existing) | strategy / risk / session / emergency / forced codes unchanged |

Journals MUST remain able to show a single closing fill with distinguishable
reason (decision and/or trade flags as implement chooses, without inventing
economics).

---

## 4. Strategy candle bar

Logical bar passed to `evaluate`:

| Field | Required |
|-------|----------|
| `open_time` | yes |
| `open` | yes |
| `high` | yes |
| `low` | yes |
| `close` | yes |
| `volume_base` / `volume_quote` | optional; unused by required 025 strategies |

Existing strategies remain close-based. New Stochastic/Keltner use high/low/close.

---

## 5. Relationships

```text
RunConfig (TP%/SL%)
    │
    ▼
BUY fill → entry_fill_price + entry_fill_candle_open_time
    │
    ├── derive take_profit_price?
    └── derive stop_loss_price?
            │
            ▼
 later closed candles (≠ entry bar) → trigger? → protective SELL intent
            │
            ▼
 Execution (mode fill) → Portfolio / journals → clear protective state
```

---

## 6. Validation summary

- TP% / SL% independently optional.
- If set: strictly positive; SL% must leave positive stop price for long.
- No mid-position mutation of % or absolute levels.
- Entry bar excluded from triggers.
