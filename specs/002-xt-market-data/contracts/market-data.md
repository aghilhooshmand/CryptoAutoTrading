# Contract: Backend Market Data

**Feature**: `002-xt-market-data`  
**Date**: 2026-08-09  
**Consumer**: Dashboard frontend and automated tests

All endpoints are public (no auth). They expose **normalized** application
models only. XT-specific field names and URLs MUST NOT appear in responses.

Base path: `/market`  
Content-Type: `application/json`

### Decimal strings

All financial numeric fields in successful JSON bodies MUST be **decimal
strings** (not JSON numbers): prices, absolute/percent changes, highs, lows,
and volumes. Example: `"65220.00"`, `"2.35"`.

### Dashboard market freshness (quote-based)

Dashboard **fresh** / **STALE** for market price and 24h stats MUST be computed
from the active quote’s `observedAt` when present, otherwise from that quote’s
`retrievedAt`. Threshold: older than **60 seconds** → `stale` when last-known
values remain visible.

Do **not** determine Dashboard market freshness from candlestick `openTime` or
from candle-series age alone. Candle `retrievedAt` is provenance only.

---

## `GET /market/pairs`

Returns supported XT Spot pairs quoted in USDT for Dashboard selection.

### Request

- Auth: none
- Query: none required

### Successful response

- HTTP `200`

```json
{
  "source": "XT",
  "retrievedAt": "2026-08-09T16:00:00.000Z",
  "pairs": [
    {
      "symbol": "btc_usdt",
      "displayName": "BTC/USDT",
      "baseCurrency": "btc",
      "quoteCurrency": "usdt",
      "status": "tradable"
    }
  ]
}
```

### Failure

| Condition | HTTP | Body intent |
|-----------|------|-------------|
| XT unreachable / timeout | `502` or `503` | Clear error; empty or omitted `pairs`; no invented symbols |
| Malformed XT payload | `502` | Clear error; no invented symbols |

Exact error shape SHOULD be consistent, e.g.:

```json
{
  "error": {
    "code": "market_data_unavailable",
    "message": "Unable to retrieve XT Spot pairs"
  }
}
```

### Acceptance mapping

| Spec | Behavior |
|------|----------|
| FR-001, FR-002 | USDT Spot pairs only; searchable list consumes this catalog |
| FR-008 | No fabricated pairs |
| FR-010 | Adapter-backed; response is normalized |

---

## `GET /market/quote`

Returns latest price and available 24h statistics for one symbol.

### Request

| Query | Required | Notes |
|-------|----------|--------|
| `symbol` | yes | e.g. `btc_usdt` |

### Successful response

- HTTP `200`

```json
{
  "symbol": "btc_usdt",
  "lastPrice": "65220.00",
  "changeAbsolute": "129.99",
  "changePercent": "0.19",
  "high24h": "65300.00",
  "low24h": "64730.08",
  "volumeBase": "1762.90919",
  "volumeQuote": "114569255.8349815",
  "source": "XT",
  "observedAt": "2026-08-09T16:00:00.000Z",
  "retrievedAt": "2026-08-09T16:00:01.000Z",
  "status": "fresh"
}
```

Notes:

- Omit optional stats that XT did not provide; do not send sentinel zeros as
  fillers unless XT actually returned zero.
- All financial fields above are decimal strings.
- `changePercent` is **percent points**, not a unit ratio: `"2.35"` means
  **+2.35%**. If XT returns a ratio (e.g. `0.0235`), the adapter MUST convert
  before responding (e.g. `"2.35"`). UI may append a `%` suffix for display
  without multiplying again.
- `status` MAY be computed server-side as `fresh` at retrieval; clients MUST
  recompute quote staleness after 60s from `observedAt` / `retrievedAt` as
  defined above.

### Error / unsupported

| Condition | HTTP | Notes |
|-----------|------|--------|
| Missing `symbol` | `400` | Validation error |
| Symbol not in supported USDT set | `404` | `status`/`code` convey `unsupported`; no fake price |
| XT failure / malformed | `502`/`503` | Clear error; no fabricated price |

### Acceptance mapping

| Spec | Behavior |
|------|----------|
| FR-003, FR-004, FR-006, FR-007 | Price, available stats, XT source, timestamps |
| FR-008, FR-009 | Fail-safe; STALE handled with last-known + label on client when aged |
| SC-002, SC-003 | Genuine mapped fields only |

---

## `GET /market/candles`

Returns historical OHLC series for one symbol and allowed interval.

### Request

| Query | Required | Notes |
|-------|----------|--------|
| `symbol` | yes | e.g. `btc_usdt` |
| `interval` | yes | Exactly one of `15m`, `1h`, `4h`, `1d` |
| `limit` | no | Server default modest (e.g. 100–200); clamp to safe max ≤ 1000 |

### Successful response

- HTTP `200`

```json
{
  "symbol": "btc_usdt",
  "interval": "1h",
  "source": "XT",
  "retrievedAt": "2026-08-09T16:00:01.000Z",
  "candles": [
    {
      "openTime": 1786287600000,
      "open": "65263.99",
      "high": "65264.00",
      "low": "65215.11",
      "close": "65228.68",
      "volumeBase": "109.08285",
      "volumeQuote": "7116784.4149678"
    }
  ]
}
```

Notes:

- OHLC and volume fields are decimal strings; `openTime` is epoch milliseconds
  (integer).
- Candle `openTime` and series `retrievedAt` MUST NOT drive Dashboard market
  **STALE** labeling (quote timestamps do).

### Error / unsupported

| Condition | HTTP | Notes |
|-----------|------|--------|
| Invalid interval | `400` | Only four intervals allowed |
| Unsupported symbol | `404` | No fake candles |
| XT failure / malformed | `502`/`503` | Clear error; empty candles not presented as success history if error |

### Acceptance mapping

| Spec | Behavior |
|------|----------|
| FR-005, FR-006 | History for allowed intervals; default UI interval `1h` |
| FR-008 | Never pad with invented candles |
| FR-013 | REST only; no streaming |

---

## Non-goals

- WebSocket streaming
- Authenticated XT / private account endpoints
- Portfolio, balances, orders, trading controls
- Sentiment / news
- Server-side persistence of favorites or last selection
- Returning raw XT envelopes to clients

## Related

- Health remains `GET /health` from Feature 001 and MUST stay distinguishable
  from market-data status.
- Data shapes: [data-model.md](../data-model.md)
- Validation scenarios: [quickstart.md](../quickstart.md)
