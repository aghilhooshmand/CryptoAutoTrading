# Data Model: Execution Abstraction (012)

**Date**: 2026-08-15  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Logical model only. **No database tables or migrations** in this feature.

---

## Entities

### ExecutionIntent

Approved (or forced-close) fill request after Controller/Risk. Mode-agnostic
payload; callers set price policy fields.

| Field | Meaning |
|-------|---------|
| `side` | `BUY` or `SELL` |
| `symbol` | Instrument id (informational for 012 economics) |
| `reference_price` | Caller-chosen reference (next-open, live mark, flatten ref) |
| `fee_rate` | Fee rate for fill math |
| `slippage_rate` | Adverse slippage rate |
| `cash` | Mode ledger cash available for BUY sizing |
| `allocated_capital` | Allocation bound for sizing |
| `max_position_size` | Max notional fraction/bound for sizing |
| `position_side` | `flat` \| `long` (current) |
| `position_qty` | Current long quantity (SELL) |
| `is_forced_close` | Hint for callers/journals; economics may ignore for sizing |

**Validation (shared economics)**:
- Unknown `side` → fail `invalid_side`
- BUY only from `flat`; else `conflicting_position_state`
- SELL only while `long` with `position_qty > 0`; else `conflicting_position_state`
- BUY dust / zero qty / insufficient cash → `insufficient_balance`
- Stable reason codes; no renames for existing Simulation/Backtest codes

### FillResult

| Field | Meaning |
|-------|---------|
| `ok` | Success / failure |
| `reason_code` | Stable code when `ok` is false (or optional diagnostic) |
| `reason_message` | Human-readable detail |
| `fill` | `FillQuote` economics on success |
| `qty` | Filled quantity on success |

**Real stub**: always `ok=false`, `reason_code=real_execution_unavailable`,
`fill`/`qty` null.

### FillQuote (existing)

Unchanged from Feature 003 accounting: reference/fill price, notional, fee,
slippage_cost, cash_delta.

### Execution mode (logical)

| Mode | Adapter | Price policy owner | Side effects owner |
|------|---------|--------------------|--------------------|
| Historical | `HistoricalExecutionAdapter` | Backtest/Comparison engine (next-open / flatten ref) | Engine state + journals; **no Portfolio** |
| Simulation | `SimulationExecutionEngine` | Pipeline / session (live safe mark) | Journals + optional Portfolio apply |
| Real | `RealExecutionAdapter` | N/A (always unavailable) | None |

---

## Relationships

```text
Controller / Risk (unchanged)
        ↓ approved intent + mode context
Mode caller (pipeline / backtest engine)
        ↓ builds ExecutionIntent (sets reference_price)
ExecutionEngine.execute
        ↓
FillResult ──► mode caller applies ledger / journal / Portfolio (Simulation only)
```

Flatten orchestration remains a **caller** concern that may still invoke the
adapter’s sell/execute path with a mode-chosen reference; it is not a separate
entity.

---

## State transitions

None at persistence layer. In-memory only:

- Intent accepted → FillResult success → caller mutates mode ledger
- Intent accepted → FillResult failure → caller journals reject; no fill apply
- Real execute → always failure; no mutation

---

## Identity & uniqueness

Not persisted. Reason code `real_execution_unavailable` is a new stable
literal for the Real stub only; existing Simulation/Backtest codes unchanged.

**Amendment 2026-08-17:** `venue_order_id` optional on `FillResult`; unused for
Kraken writes until Feature 015.
