# Research: XT Spot Market Data

**Feature**: `002-xt-market-data`  
**Date**: 2026-08-09

## Decision 1: XT public Spot REST surface (verified)

**Decision**: Use XT Spot public REST base `https://sapi.xt.com` with these
read-only endpoints (verified live on 2026-08-09):

| Need | Endpoint | Notes |
|------|----------|--------|
| Pair universe | `GET /v4/public/symbol` | Envelope `{ rc, mc, result.symbols[] }`; filter `quoteCurrency == "usdt"`, prefer `state == "ONLINE"` and `tradingEnabled` / `openapiEnabled` |
| Latest price + 24h stats | `GET /v4/public/ticker?symbol={symbol}` | Envelope `{ rc, mc, result: [ticker] }`; symbol form `btc_usdt` |
| Candlesticks | `GET /v4/public/kline?symbol={symbol}&interval={interval}&limit={n}` | Envelope `{ rc, mc, result: [bar...] }`; intervals `15m`, `1h`, `4h`, `1d` all return SUCCESS |

**Ticker field mapping (XT → meaning)** — short keys observed live:

| XT key | Internal meaning |
|--------|------------------|
| `s` | symbol |
| `t` | observation/trade time (ms) |
| `c` | last / close price |
| `o` | 24h open |
| `h` | 24h high |
| `l` | 24h low |
| `cv` | absolute change |
| `cr` | change ratio |
| `q` | base volume |
| `v` | quote volume |

**Kline bar mapping**: `t` (open time ms), `o`, `h`, `l`, `c`, `q` (base vol), `v` (quote vol).

**Rationale**: Current XT Spot public market surface (not legacy
`/data/api/v1/*`) matches Feature 002 needs without credentials. Live probes
confirmed USDT filtering (~400+ ONLINE/openapi USDT pairs) and all four chart
intervals.

**Alternatives considered**:
- Legacy v1 docs (`xtpub/api-doc`): outdated relative to `sapi.xt.com/v4`.
- Futures hosts (`fapi.xt.com` / `dapi.xt.com`): out of scope (Spot only).
- Calling XT directly from the browser: CORS/rate-limit opacity; breaks adapter
  isolation and leaks exchange coupling into Dashboard code.
- CCXT library: heavier dependency for three public GETs; still would wrap XT.

## Decision 2: Adapter + normalization boundary

**Decision**: Introduce `MarketDataAdapter` (protocol) with an `XtSpotAdapter`
implementation under `backend/app/market_data/adapters/`. Adapter owns XT URLs,
envelope parsing (`rc == 0` / `mc == SUCCESS`), short-key mapping, and HTTP
errors. `service.py` returns only internal models. FastAPI routes and frontend
never see XT payload shapes.

**Rationale**: Constitution XVI + FR-010. Keeps Dashboard and future control
plane free of XT churn.

**Alternatives considered**:
- Map XT JSON directly in route handlers: faster short-term, couples API to XT.
- Share XT types to frontend: violates adapter isolation and FR-010.

## Decision 3: Application HTTP API (backend for frontend)

**Decision**: Expose three read endpoints under `/market`:

- `GET /market/pairs` — supported USDT Spot pairs
- `GET /market/quote?symbol=` — normalized quote + status metadata
- `GET /market/candles?symbol=&interval=` — normalized OHLC series

Vite proxy extends from `/health` to also forward `/market` to the backend.

**Rationale**: Thin BFF preserves Feature 001 proxy pattern, hides XT from the
browser, and gives a stable contract for tests.

**Alternatives considered**:
- Single aggregated Dashboard payload: fewer round-trips, harder partial
  refresh/error isolation.
- GraphQL: unnecessary for three reads.

## Decision 4: HTTP client and timeouts

**Decision**: Use `httpx` AsyncClient (runtime dependency) with a short timeout
(e.g. 10s) for XT calls. Treat non-success envelopes, HTTP errors, timeouts,
and schema validation failures as unavailable/error — never invent prices.

**Rationale**: httpx is already present for FastAPI TestClient usage; promoting
it to runtime keeps one HTTP stack. Fail-safe aligns with FR-008/FR-009.

**Alternatives considered**:
- `urllib` / stdlib only: workable but less ergonomic with async FastAPI.
- Retries with backoff: optional later; keep Feature 002 simple unless flaky
  local networks force a single retry.

## Decision 5: Freshness, STALE, and refresh

**Decision**:
- Freshness threshold: **60 seconds** since last successful observation
  timestamp carried with the quote/series (or client receipt time if XT omits
  usable time — prefer XT `t` when present).
- Status values: `loading` | `fresh` | `stale` | `unavailable` | `unsupported` | `error`.
- When `stale`, last-known values MAY remain visible with explicit **STALE**
  labeling; never imply fresh/current.
- Manual refresh control is required.
- Optional light auto-refresh: **60s** interval when enabled, refreshing only
  the active symbol’s quote + candles (and not hammering `/symbol`). Keep off
  by default or behind a simple toggle; skip if it adds non-trivial complexity
  during implement.

**Rationale**: Spec assumptions + user direction. 60s auto-refresh matches the
stale threshold and stays well under typical public IP rate limits for ~2
requests per minute per operator.

**Alternatives considered**:
- 30s auto-refresh: more load for little Dashboard value.
- WebSocket streams: explicitly out of scope.
- Hide stale values: worse UX; clarification chose labeled last-known.

## Decision 6: Race-safe pair/interval changes

**Decision**: Frontend request generation counter (or AbortController): ignore
responses whose request id is older than the latest selection. Changing pair
or interval bumps the generation and shows loading for the new selection.
Backend remains stateless per request.

**Rationale**: Spec edge cases require no permanent mismatch of pair/price or
interval/series.

**Alternatives considered**:
- Backend cancellation tokens: unnecessary for short REST GETs.
- Debounce-only: reduces races but does not eliminate slow-response overwrites.

## Decision 7: Charting library

**Decision**: Use **lightweight-charts** for responsive candlestick rendering
of normalized OHLC bars.

**Rationale**: Purpose-built for candles, small footprint, works in React via a
ref + effect, suitable for phone-width. Dashboard still consumes normalized
series only.

**Alternatives considered**:
- Recharts: excellent for lines/bars; candlesticks need more custom work.
- Chart.js financial plugin: heavier / less idiomatic for this stack.
- SVG/table-only: simplest, weaker market readability for SC-004.

## Decision 8: Local preferences and favorites

**Decision**: Persist in `localStorage` keys scoped to this app, e.g.:

- last selected symbol
- last selected interval (`15m`|`1h`|`4h`|`1d`, default `1h`)
- favorite symbol list (ordered)

Favorites render above the searchable full list. Invalid persisted symbols
fall back to default pair rules (prefer `btc_usdt` if present). Favorites that
are no longer supported are hidden/removed. No SQL and no server preference
API.

**Rationale**: FR-018/FR-019 and user direction. UI prefs ≠ domain persistence.

**Alternatives considered**:
- SQLite preference tables: rejected for this feature (Complexity Tracking).
- Cookies: unnecessary; `localStorage` is enough for same-device reload.

## Decision 9: Pair universe filtering and defaults

**Decision**: Supported pairs = XT Spot symbols with `quoteCurrency == "usdt"`
and tradable/openapi-friendly state when those flags exist. Default first load
(no valid persistence): `btc_usdt` if present, else first available USDT pair,
else empty/unavailable.

**Rationale**: Spec clarifications and assumptions.

**Alternatives considered**:
- All quote currencies: out of scope.
- Hard-coded top-N pairs only: simpler but contradicts searchable full USDT
  universe requirement.

## Decision 10: Rate-limit posture

**Decision**: Do not scrape all tickers on a timer. Load pair list on Dashboard
entry (cache in memory for the session or until manual pair-list refresh).
Quote + candles fetch on selection change, manual refresh, and optional 60s
auto-refresh for the **active** pair only. Cap candle `limit` modestly (e.g.
100–200, well under XT spot max ~1000).

**Rationale**: Keeps traffic low vs public IP limits; intentional simplicity.

**Alternatives considered**:
- Polling all USDT tickers: wasteful and rate-limit risky.
- Aggressive multi-retry storms: can worsen bans; fail clearly instead.
