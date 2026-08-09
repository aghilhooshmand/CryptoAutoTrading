# Data Model: XT Spot Market Data

**Feature**: `002-xt-market-data`  
**Date**: 2026-08-09

Internal application models only. XT short-key payloads MUST NOT leak past the
adapter boundary.

## TradingPair

A selectable XT Spot instrument quoted in USDT.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `symbol` | string | yes | Canonical id, lowercase underscore form (e.g. `btc_usdt`) |
| `displayName` | string | yes | Human label (e.g. `BTC/USDT`) |
| `baseCurrency` | string | yes | e.g. `btc` |
| `quoteCurrency` | string | yes | Always `usdt` for Feature 002 |
| `status` | string | yes | Normalized availability, e.g. `tradable` / `unavailable` |

### Validation

- `quoteCurrency` MUST equal `usdt` (case-normalized) before exposure.
- Empty universe → empty list; never invent pairs.
- Unsupported/unknown symbol requests → `unsupported` market status, no fake quote.

### Relationships

- Referenced by `MarketQuote.symbol`, `CandlestickSeries.symbol`, `PairFavorite.symbol`, and Dashboard prefs.

## Numeric representation

All financial numeric fields in internal models and HTTP contracts MUST be
**decimal strings** (e.g. `"65220.00"`, `"2.35"`). Do not expose JSON numbers
for prices, changes, highs, lows, or volumes—avoids implicit floating-point
semantics at the API boundary. Non-financial fields (timestamps, enums,
counts such as candle `openTime` epoch ms) keep their own types.

## MarketQuote

Latest price and available 24h statistics for one pair, plus provenance.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `symbol` | string | yes | Must match requested pair |
| `lastPrice` | decimal string | yes* | *Required for a successful fresh/stale quote; omit on error |
| `changeAbsolute` | decimal string | no | Absolute price change when present |
| `changePercent` | decimal string | no | Percent points: `"2.35"` means **+2.35%**, not a ratio `0.0235` |
| `high24h` | decimal string | no | Show only when present |
| `low24h` | decimal string | no | Show only when present |
| `volumeBase` | decimal string | no | Base asset volume when present |
| `volumeQuote` | decimal string | no | Quote asset volume when present |
| `source` | string | yes | `"XT"` for this feature |
| `observedAt` | ISO-8601 datetime | yes* | From XT ticker time when available; else server observation time |
| `retrievedAt` | ISO-8601 datetime | yes | Backend receipt/normalization time |

\* On failure responses, quote body may be null while status carries the error.

### Validation

- Never invent missing stats; omit fields.
- Reject malformed adapter output rather than guessing.
- `source` for successful XT retrieval MUST identify XT.
- If XT supplies change as a ratio (e.g. `0.0235`), the adapter MUST convert to
  percent points before exposure (e.g. `"2.35"`).

## Candlestick

One OHLC bar.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `openTime` | integer (epoch ms) | yes | Bar open time; **not** used for Dashboard freshness |
| `open` | decimal string | yes | |
| `high` | decimal string | yes | |
| `low` | decimal string | yes | |
| `close` | decimal string | yes | |
| `volumeBase` | decimal string | no | |
| `volumeQuote` | decimal string | no | |

## CandlestickSeries

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `symbol` | string | yes | |
| `interval` | enum | yes | `15m` \| `1h` \| `4h` \| `1d` |
| `candles` | Candlestick[] | yes | Ordered; may be shorter than requested; never pad with fakes |
| `source` | string | yes | `"XT"` |
| `retrievedAt` | ISO-8601 datetime | yes | Retrieval metadata only; **not** the Dashboard STALE clock |

### Validation

- Interval MUST be one of the four allowed values; default UI interval is `1h`.
- Empty series on success is allowed (show empty state); failures use status/error path.
- Do **not** derive Dashboard market freshness/STALE from candle `openTime` or
  series `retrievedAt`.

## MarketDataStatus

User-visible readiness for the Dashboard **market quote** section (price/stats
freshness). Driven by quote timing only.

| Value | Meaning | Values visible? |
|-------|---------|-----------------|
| `loading` | Request in flight for current selection | Prior values may remain only if clearly not claimed as current selection’s fresh data |
| `fresh` | Successful **quote** younger than 60s | Yes, as current |
| `stale` | Last known **quote** older than 60s | Yes, with explicit **STALE** label; MUST NOT present as fresh/current |
| `unavailable` | No data / empty universe / XT down without usable payload | No fabricated numbers |
| `unsupported` | Symbol not in supported USDT set | No fabricated numbers |
| `error` | Transport/parse/validation failure | No fabricated numbers |

### Rules

- Freshness threshold: **60 seconds** from the quote’s `observedAt` when present;
  otherwise from the quote’s `retrievedAt`.
- Do **not** use candlestick `openTime` (or candle-series age alone) to mark the
  Dashboard market view STALE.
- STALE last-known price/stats MAY remain visible with status `stale`.
- Process health (`GET /health`) MUST remain distinguishable from market-data status.

## PairFavorite

Local-only Dashboard selection aid.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `symbol` | string | yes | Must be a currently supported USDT pair to display |
| `addedAt` | ISO-8601 | no | Optional ordering aid |

### Rules

- Stored only in browser `localStorage`.
- Appears before the full searchable list.
- MUST NOT create portfolio, balances, positions, or Auto Trading configuration.
- Drop/hide favorites that are no longer supported.

## DashboardMarketPreferences (client)

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `lastSymbol` | string | no | Restored when still supported |
| `lastInterval` | enum | no | One of `15m`/`1h`/`4h`/`1d`; default `1h` |
| `favorites` | string[] | no | Symbols |

### State transitions (selection)

```text
[no prefs] --> select default pair (btc_usdt if available) + interval 1h
[prefs] --> restore lastSymbol/lastInterval if valid else fallback default
user changes pair/interval --> persist + bump request generation + loading
quote age < 60s (observedAt else retrievedAt) --> fresh
quote age >= 60s (no newer quote success) --> stale (keep last-known + STALE)
failure --> error/unavailable/unsupported (no fabricated values)
# candle openTime never drives the fresh/stale transition above
```

## Exchange Market Data Adapter (logical)

Not a persisted entity. Boundary object that:

1. Calls XT public REST.
2. Validates envelopes and maps to `TradingPair` / `MarketQuote` / `CandlestickSeries`.
3. Surfaces typed failures for the service layer.

Only the XT adapter implementation may know XT URLs and payload keys.
