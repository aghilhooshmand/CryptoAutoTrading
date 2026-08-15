# Implementation Plan: Trading & Experiment Defaults

**Branch**: `008-trading-experiment-defaults` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-trading-experiment-defaults/spec.md`  
(including Session 2026-08-12 clarifications)

## Summary

Add a local **Settings** surface under Auto Trading for reusable operator
defaults (market, capital nesting, costs, optional risk, preferred strategy +
registry-driven params). Persist a singleton document in SQLite behind
`GET`/`PUT`/`POST …/reset` `/settings`. Simulation, Backtest, and Comparison
**fresh** create forms initialize from saved Settings (comparison: first leg
only). Explicit Save/Reset; defaults never rewrite historical effective
configs; no trading authority or second engine.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: Existing FastAPI + SQLAlchemy + SQLite; Vite + React.
Reuse capital nesting validation, `validate_and_materialize`,
`StrategyConfigFields` / `GET /strategies`, and shared cost helpers. New thin
Settings package + API + Auto Trading tab only.

**Storage**: SQLite singleton `operator_defaults` (or equivalent) in the shared
local DB (`backend/data/simulation.db`). No Settings version history in v1.

**Testing**: pytest unit (starters, validation reject leaves last good, reset,
corrupt fail-closed) + contract (`GET`/`PUT`/`POST reset`); Vitest Settings
tab (Save/Reset, strategy param reset on strategy change, ~375px usability
smoke) + create-form init from mocked Settings (fresh open only; comparison
leg 0 only).

**Target Platform**: Local developer machines; phone-width ~375px

**Project Type**: Web application (`backend/` + `frontend/`)

**Performance Goals**: Settings read/write are local DB ops (trivial latency).
No dedicated SLO gate.

**Constraints**:
- Defaults only — copy on fresh form open; never mutate historical configs
- Explicit Save; unsaved draft does not seed forms; Settings draft survives tab switches until Save/Reset/reload
- Fail-closed Settings reads expose `warning` in Settings UI (FR-014)
- Explicit Reset persists product starters; no trading side effects
- Registry-driven strategy params; no hard-coded Dual-EMA-only Settings fields
- One shared starter set (capital `1000`; optional risk unset)
- Simulation keeps its own required risk validation when Settings leave rates unset
- Auto Trading Settings tab only (no 4th primary nav)
- No cloud sync, credentials, real-money, GE experiment knobs, or default windows
- No second trading engine; no Controller → Risk → Execution bypass
- Package path locked: `backend/app/settings/`

**Scale/Scope**: Single local operator; one Settings document; three create
forms + Settings tab

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Settings validate nesting; do not bypass Risk |
| II Simulation before real money | Pass | Defaults only; no real-money path |
| III–IV Pipeline / controller–risk | Pass | Settings never call trading pipeline |
| V Explicit session boundaries | Pass | Optional risk unset in Settings; Sim validates at create |
| VI Net P&L | Pass | Fee/slippage defaults only; accounting unchanged |
| VII Decision traceability | Pass | Effective configs remain per artifact |
| VIII Fail safe | Pass | Invalid Save rejected; corrupt read → starters |
| IX Emergency stop | Pass | N/A; Settings do not control live trading |
| X Intentional simplicity | Pass | Singleton + thin API; reuse validators/UI |
| XI Conventional strategies | Pass | Registry-driven preferred strategy |
| XII Evidence, not guarantees | Pass | No profit claims |
| XIII Three primary UI areas | Pass | Settings under Auto Trading |
| XIV Responsive UX | Pass | ~375px; explicit Save/Reset |
| XV Python / React / SQL | Pass | SQLite singleton |
| XVI–XVIII Adapter / credentials | Pass | No credentials; public data unrelated |
| XIX–XXVI Sentiment | Pass | Out of scope |
| XXVII–XXIX Spec-driven / tests | Pass | Contracts + unit/contract/UI tests |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — no unjustified complexity.

### Post-design Constitution Check

After Phase 1 artifacts: still **PASS**. Design adds a Settings singleton and
read/write/reset API plus form seeders; Controller/Risk/Execution and strategy
modules stay authoritative for trading; historical effective configs remain
independent of Settings.

## Project Structure

### Documentation (this feature)

```text
specs/008-trading-experiment-defaults/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── operator-defaults-api.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   └── settings.py              # NEW — GET/PUT /settings, POST /settings/reset
│   ├── settings/                    # NEW package (canonical: app.settings)
│   │   ├── service.py               # Load/save/reset + validation
│   │   ├── starters.py              # ProductStarterDefaults constants
│   │   └── repository.py            # Singleton row access
│   ├── db/models.py                 # ADD OperatorDefaultsRow (or equivalent)
│   └── main.py                      # Mount settings router
└── tests/
    ├── unit/test_settings_*.py
    └── contract/test_settings_api.py

frontend/
├── src/
│   ├── features/settings/           # NEW Settings panel/tab form
│   ├── features/simulation/         # EXTEND fresh init from Settings
│   ├── features/backtest/           # EXTEND fresh init from Settings
│   ├── features/comparison/         # EXTEND shared + leg0 from Settings
│   ├── pages/AutoTradingPage.tsx    # ADD Settings tab
│   ├── services/settingsApi.ts      # NEW
│   └── __tests__/settings*.test.tsx
└── ...
```

**Structure Decision**: Extend existing backend/frontend app. New thin Settings
module + API; reuse strategy registry UI and money validation patterns. No new
primary navigation area.

## Complexity Tracking

> No constitution violations requiring justification.
