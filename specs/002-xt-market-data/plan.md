# Implementation Plan: XT Spot Market Data

**Branch**: `002-xt-market-data` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-xt-market-data/spec.md`

## Summary

Extend the Feature 001 shell so the Dashboard shows genuine XT.COM public Spot
market data for USDT-quoted pairs: searchable pair selection (with local
favorites), latest price and available 24h stats, candlestick history for
intervals `15m` / `1h` / `4h` / `1d` (default `1h`), explicit XT source/status
(including STALE after 60s), and manual refresh. XT REST access is confined to
a backend market-data adapter that normalizes payloads into internal models;
the frontend consumes only application HTTP contracts. No credentials, private
APIs, WebSockets, trading, sentiment, portfolio math, or SQL preference store.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript + React 18+ (frontend)

**Primary Dependencies**: FastAPI + Uvicorn + httpx (backend XT client);
Vite + React Router + Lucide React (existing); lightweight-charts (Dashboard
candlesticks)

**Storage**: No SQL for this feature. Dashboard preferences (last pair, last
interval, favorites) use browser `localStorage` only. Domain/trading
persistence remains deferred until a later feature that needs SQL.

**Testing**: pytest (backend market-data contracts + adapter mapping/unit);
Vitest + React Testing Library (Dashboard pair/status/race/prefs behavior;
chart library may be lightly mocked)

**Target Platform**: Local developer machines via browser; phone-width
validation at ~375px viewport

**Project Type**: Web application (existing `backend/` + `frontend/` layout)

**Performance Goals**: Successful Dashboard refresh shows XT-sourced pair,
price, source, and last-update within 5 seconds of a completed refresh locally
(SC-002); pair selection and status remain usable on ~375px (SC-006)

**Constraints**: Public XT Spot REST only (`https://sapi.xt.com`); no API keys;
no private endpoints; no WebSocket streaming; no fabricated values; stale
threshold 60 seconds; race-safe pair/interval changes; adapter isolation; no
trading/simulation/risk/strategies/portfolio/sentiment/news/auth/futures/
margin/leverage

**Scale/Scope**: Single local operator; one Dashboard market-data surface; XT
USDT Spot pair universe (~hundreds of symbols); three thin backend read APIs
plus Dashboard UI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Read-only public market data; no orders or capital paths |
| II Simulation before real money | Pass | Neither mode implemented |
| III–IV Trading pipeline / controller | Pass | No strategy→order paths |
| V–IX Session bounds, P&L, journals, fail-safe, stop | Pass | Fail-safe market status only; trading controls deferred |
| X Intentional simplicity | Pass | REST adapter + thin APIs + Dashboard UI; optional auto-refresh only if trivial |
| XI–XII Strategies / no guaranteed profit | Pass | No strategies or P&L claims |
| XIII Exactly three primary UI areas | Pass | Market data extends Dashboard only; Auto Trading / Portfolio stay placeholders |
| XIV Responsive UX | Pass | Pair/price/status/history usable at ~375px |
| XV Python / React / SQL direction | Pass* | Python 3.12 + React retained; see Complexity Tracking for localStorage prefs |
| XVI–XVIII Exchange adapter / credentials / withdrawals | Pass | XT confined to adapter; no credentials; no withdrawals |
| XIX–XXVI Market sentiment | Pass | Explicitly out of scope for Feature 002 (future Dashboard capability) |
| XXVII–XXIX Spec-driven / tests / source of truth | Pass | Spec→plan→contracts/tests; XT docs verified before endpoint lock |
| XXX Git commit traceability | Pass | Propose commits; do not auto-commit |

**Gate result**: PASS — one justified complexity note below.

### Post-design Constitution Check

Re-evaluated after `research.md`, `data-model.md`, `contracts/`, and
`quickstart.md`: still PASS. Adapter boundary, public-only access, fail-safe
status model, and Dashboard-only scope remain intact. No new unjustified
complexity.

## Project Structure

### Documentation (this feature)

```text
specs/002-xt-market-data/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── market-data.md
└── tasks.md              # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                 # add httpx as runtime dependency
├── app/
│   ├── main.py                    # mount market-data router; keep /health
│   ├── api/
│   │   ├── health.py
│   │   └── market_data.py         # GET /market/pairs|quote|candles
│   └── market_data/
│       ├── __init__.py
│       ├── models.py              # internal Pydantic models
│       ├── service.py             # orchestration over adapter
│       └── adapters/
│           ├── __init__.py
│           ├── base.py            # MarketDataAdapter protocol
│           └── xt_spot.py         # XT public REST client + normalization
└── tests/
    ├── contract/
    │   ├── test_health.py
    │   └── test_market_data.py
    └── unit/
        └── test_xt_spot_adapter.py

frontend/
├── package.json                   # add lightweight-charts
├── vite.config.ts                 # proxy /health + /market
├── src/
│   ├── pages/
│   │   └── DashboardPage.tsx      # compose market-data UI
│   ├── features/
│   │   └── market-data/
│   │       ├── PairSelector.tsx
│   │       ├── MarketQuotePanel.tsx
│   │       ├── CandleChart.tsx
│   │       ├── MarketStatusBadge.tsx
│   │       ├── useMarketData.ts   # fetch + race guard + optional auto-refresh
│   │       └── prefs.ts           # localStorage pair/interval/favorites
│   ├── services/
│   │   └── marketDataApi.ts       # typed calls to backend contracts
│   └── __tests__/
│       └── ...                    # prefs, race guard, status labeling
```

**Structure Decision**: Keep Feature 001 dual-package layout. Add
`backend/app/market_data/` for adapter + models + service, thin FastAPI routes
under `api/`, and a focused `frontend/src/features/market-data/` module so
Dashboard presentation never imports XT types or URLs.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution XV SQL persistence vs browser `localStorage` for pair/interval/favorites | Spec FR-018/FR-019 require local-device Dashboard selection prefs without accounts or server preference store; user direction forbids SQL just for Dashboard preferences | SQLite/Postgres preference tables would add ORM/migration surface with no multi-device or server requirement; UI prefs are not domain trading state |
