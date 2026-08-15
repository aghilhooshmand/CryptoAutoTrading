# Research: Trading & Experiment Defaults

**Feature**: `008-trading-experiment-defaults`  
**Date**: 2026-08-12  
**Spec**: [spec.md](./spec.md)

## Decision 1: Persist Settings in SQLite via a thin API (not browser-only)

**Decision**: Store a single local **OperatorDefaults** document in the existing
SQLite database (`backend/data/simulation.db`) behind:

- `GET /settings` — current effective defaults (saved or product starters)
- `PUT /settings` — explicit Save with domain validation
- `POST /settings/reset` — persist product starters as active Settings

Frontend Settings UI and create-form seeders consume this API. Do **not** use
Dashboard-style `localStorage` as the source of truth for trading defaults.

**Rationale**:
- Spec requires explicit Save, invalid-save leave-last-good, and the same
  capital / strategy validation as trading forms — already implemented on the
  backend (`_validate_capital`, `validate_and_materialize`).
- Constitution XV prefers SQLite for local persistence; Settings are
  operator-local config, not exchange secrets.
- Survives clearing unrelated browser prefs; one machine, one DB path via
  existing `SIMULATION_DB_PATH` / `BACKTEST_DB_PATH`.

**Alternatives considered**:
- **Frontend `localStorage` only** (mirror `prefs.ts`) — rejected: duplicates
  validation, drifts from backend nesting/param rules, weaker fail-closed story.
- **JSON file beside the DB** — rejected: second persistence channel without
  gain; SQLAlchemy + existing migrations pattern is enough.
- **Cloud / multi-user profiles** — out of scope (FR-009).

## Decision 2: Singleton row; no Settings history / versioning in v1

**Decision**: One logical Settings record (singleton table or fixed `id=1`
row). Overwrite on successful Save/Reset. No audit log of Settings changes in
v1.

**Rationale**: Spec entities are current OperatorDefaults + ProductStarters;
history belongs on run/session effective configs, not Settings.

**Alternatives considered**:
- Append-only Settings versions — unnecessary for FR-001–007.
- Soft-delete / multi-profile — out of scope.

## Decision 3: One shared product-starter set (capital 1000; optional risk unset)

**Decision**: Product starter defaults (and Reset target) are a **single** set
used by Settings and by all three create forms when no valid saved Settings
exist:

| Field | Starter |
|-------|---------|
| `symbol` | `btc_usdt` |
| `timeframe` | `1h` |
| Capital nesting | `1000` / `1000` / `1000` |
| `feeRate` / `slippageRate` | `0.002` / `0.0005` (code `DEFAULT_*`) |
| `targetNetProfitRate` / `maxSessionLossRate` / `maxTrades` | unset (`null`) |
| Preferred strategy | `dual_ema` + registry param defaults |

**Intentional UI change**: Today Simulation form hard-codes capital `500` and
pre-fills required risk rates `0.01` / `0.007`. After this feature, a **fresh**
Simulation form initializes from Settings (starters or saved). When risk rates
are unset in Settings, Simulation leaves them empty and keeps **its own**
required validation at create/start (clarify Q5 / FR-013). Backtest and
Comparison continue to treat omitted rates as not applied.

**Rationale**: Spec assumption explicitly cites capital nesting of 1000 and
optional risk unset; one Settings document cannot honestly mirror both Sim-500
and BT-1000 starters.

**Alternatives considered**:
- Per-mode Settings (sim vs backtest) — rejected for v1 scope (FR-002 is one
  defaults set).
- Keep Simulation’s 500/required rates as hard-coded overrides after Settings
  load — rejected (defeats SC-001).

## Decision 4: Settings tab under Auto Trading (not a 4th primary area)

**Decision**: Add a **Settings** tab beside Simulation / Backtest / Comparison
on `AutoTradingPage` (`role="tablist"`). No new primary nav item; no
`/settings` primary route required (optional deep-link later).

**Rationale**: FR-010 / constitution XIII — Settings is a secondary surface
under Auto Trading.

**Alternatives considered**:
- Fourth primary nav “Settings” — rejected (FR-010).
- Modal-only Settings — weaker discoverability; tab matches Comparison pattern.

## Decision 5: Apply Settings only on fresh create-form open

**Decision**: Extract a shared client helper (and thin API client) that maps
`GET /settings` → form initial state. Forms call it when:

1. Mounting a **new** create draft, or
2. Resetting the form after successful create / explicit discard that clears
   the draft.

Do **not** subscribe Settings changes into an in-progress draft (clarify Q2 /
FR-004). Comparison: map preferred strategy + params to **leg 0 only**; leg 1+
keep today’s product/registry starters (e.g. RSI defaults).

**Rationale**: Locked clarifications; prevents “Settings overwrite mid-edit.”

**Alternatives considered**:
- Live-bind forms to Settings store — rejected (Q2).
- Prefill all comparison legs from preferred strategy — rejected (Q1).

## Decision 6: Preferred-strategy change resets params in Settings draft

**Decision**: Settings UI reuses `StrategyConfigFields` behavior: changing
`strategyId` replaces `strategyParams` with `defaultParamsFor(newId)` /
registry defaults before Save (clarify Q4 / FR-003).

**Rationale**: Already implemented for trading forms; avoids param carry-over
bugs across schemas.

## Decision 7: Settings never touch the trading pipeline

**Decision**: Settings service only validates and persists OperatorDefaults.
It MUST NOT call session start/stop, backtest create, comparison create, or
Controller / Risk / Execution.

**Rationale**: FR-008 / FR-012 / constitution I–IV.

## Decision 8: Corrupted / unknown strategy fail-closed to starters (with signal)

**Decision**: On read: if stored JSON is corrupt or fails validation, return
product starters and a clear flag/message (e.g. `source: "starters"` +
`warning`) so UI can show that saved Settings could not be used. On Save: if
`strategyId` is unknown or params invalid, reject with the same error class as
create APIs; last good row unchanged.

**Rationale**: Spec edge cases; fail-safe (constitution VIII) without inventing
hard-coded Dual EMA-only fields.

## Resolved Technical Context items

| Item | Resolution |
|------|------------|
| Storage technology | SQLite singleton via Settings API |
| Product starter capital | Unified `1000` nesting |
| Simulation vs Settings risk optionality | Settings optional; Sim validates at create |
| UI placement | Auto Trading → Settings tab |
| Form re-apply timing | Fresh open only |
| Comparison leg seeding | First leg only |
