# Implementation Plan: XT Spot Market Data

**Branch**: `002-xt-market-data` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-xt-market-data/spec.md`

## Summary

Extend the Feature 001 shell so the Dashboard shows genuine XT.COM public Spot
market data for USDT-quoted pairs: searchable pair selection (with local
favorites), latest price and available 24h stats, candlestick history for
intervals `15m` / `1h` / `4h` / `1d` (default `1h`), explicit XT source/status
(including STALE after 60s), and manual refresh. XT REST access is confined to
a backend market-data adapter that normalizes payloads into internal models
(financial values as decimal strings; `changePercent` as percent points);
the frontend consumes only application HTTP contracts. Dashboard freshness/
STALE is quote-timed (60s). Manual refresh is required; auto-refresh is
optional polish and must not block completion. No credentials, private
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
no private endpoints; no WebSocket streaming; no fabricated values; financial
API fields as decimal strings; `changePercent` in percent points; quote-based
stale threshold 60 seconds (not candle `openTime`); race-safe pair/interval
changes; adapter isolation; manual refresh required; auto-refresh optional
polish only; no trading/simulation/risk/strategies/portfolio/sentiment/news/
auth/futures/margin/leverage

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
| X Intentional simplicity | Pass | REST adapter + thin APIs + Dashboard UI; auto-refresh optional polish only (not required for completion) |
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
│   │       ├── useMarketData.ts   # fetch + race guard; auto-refresh optional polish only
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

---

## Amendment 2026-08-17 — Kraken-first public implementation plan

**Status**: This is the implementation plan for the living Feature 002 work.
Historical XT plan above remains the as-built record.

### Summary

Make **Kraken** the default/active public market-data venue. Add
`KrakenPublicAdapter` (name may vary) behind the existing `MarketDataAdapter`
boundary. Introduce product identity (`venue`, `base_asset`, `quote_asset`,
`canonical_symbol`, `venue_product_id`). Keep `XtSpotAdapter` for `venue=xt`
regression. Persist identity on new sessions/backtests/settings. Do not
implement Kraken private API or Real orders. Do not change Strategy,
Controller, or Risk semantics. Do not globally replace USDT with EUR.

Implementation order for the migration (this feature is step 2 after the
minimal constitution/identity docs):

1. Identity models + additive DB columns + legacy NULL→XT inference
2. Generalized adapter protocol (`list_spot_pairs`, not USDT-only protocol)
3. Kraken public adapter (pairs, ticker, OHLC, mapping, stale)
4. Service factory: default `kraken`; explicit `xt`
5. HTTP contracts + Dashboard/Settings defaults
6. Sim/Backtest/comparison fetch matching venue only
7. Minimum 009 valuation identity (quote_asset; no Sim→Kraken book)
8. Tests (FR-037)

### Technical Context (amendment)

**Language/Version**: Unchanged (Python 3.12, React/TS)

**Primary Dependencies**: Existing `httpx`; Kraken public REST
`https://api.kraken.com` (verify AssetPairs / Ticker / OHLC at implement)

**Storage**: Additive SQLite columns on `simulation_sessions`, backtest runs,
comparison runs/legs as needed, `operator_defaults`, and Simulation Portfolio
`quote_asset` (default existing book `usdt`). Nullable on legacy rows.
Dashboard prefs remain `localStorage` but MUST key venue+product (do not send
XT ids to Kraken).

**Testing**: New Kraken adapter unit tests from recorded public payloads;
contract tests default Kraken; pin existing XT tests to `venue=xt`; recorded
candle Sim/Backtest invariance.

**Constraints**: No Kraken keys in 002. No mix of venues. No XT class rename.
No Coinbase. Constitution XVI venue isolation.

### Constitution Check (amendment)

| Principle | Status | Notes |
|-----------|--------|-------|
| I–V Capital / pipeline / controller | Pass | Public data only; no orders |
| XVI Exchange isolation | Pass | Kraken types in adapter; core venue-neutral |
| XVII Public/private | Pass | No private Kraken |
| XVIII Credentials | Pass | None required |
| XXVIII–XXIX Tests / continuity | Pass | XT regression pinned; engine invariance |
| XXXII Execution abstraction | Pass | No Real writes |
| XXXIX Real-money enablement | Pass | Real orders deferred to 015 after 013 |

**Gate result**: PASS for public-data amendment.

### Phase 0 research (amendment)

See [research.md](./research.md) Decision 12 (Kraken public REST). Verify live
AssetPairs/Ticker/OHLC and XBT→BTC mapping before locking endpoints.

### Phase 1 design (amendment)

- [data-model.md](./data-model.md) identity fields
- [contracts/market-data.md](./contracts/market-data.md) living contract
- [quickstart.md](./quickstart.md) Kraken default curls
- Minimum 009/010/012 spec notes (quote_asset, venue_order_id additive)

### Project structure (additive)

```text
backend/app/market_data/adapters/kraken_public.py   # new
backend/app/market_data/adapters/xt_spot.py         # keep, legacy
backend/app/market_data/adapters/base.py            # generalize protocol
backend/app/market_data/models.py                   # identity fields
backend/app/market_data/service.py                  # venue factory, default kraken
backend/app/db/models.py                            # additive columns
backend/app/db/session.py                           # additive migrations
backend/app/settings/starters.py                    # Kraken-first defaults
backend/app/portfolio/identity.py                   # quote_asset role (min)
backend/app/portfolio/valuation.py                  # venue product, not _usdt hardcode
backend/app/execution/port.py                       # venue_order_id additive only
```

Do **not** delete `xt_spot.py` or XT tests.
