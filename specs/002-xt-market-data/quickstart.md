# Quickstart: XT Spot Market Data

**Feature**: `002-xt-market-data`  
**Date**: 2026-08-09

Validate Feature 002 end-to-end against [contracts/market-data.md](./contracts/market-data.md)
and [data-model.md](./data-model.md). No XT credentials are required.

## Prerequisites

- Feature 001 shell runnable (Python 3.12+, Node.js for Vite)
- Network access to `https://sapi.xt.com` from the machine running the backend
- Repo root: `CryptoAutoTrading`

## Setup

```bash
# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/dashboard` (Vite should proxy `/health` and
`/market` to the backend).

## Automated checks

```bash
# Backend
cd backend && source .venv/bin/activate
pytest

# Frontend
cd frontend && npm test
```

Expected: existing Feature 001 health/nav tests still pass; new market-data
contract/unit and Dashboard preference/status tests pass.

## Manual validation scenarios

### 1. Genuine XT quote without credentials (P1)

1. Start backend + frontend with **no** XT API keys in env or config.
2. Open Dashboard.
3. Confirm a supported USDT pair (default preferably `BTC/USDT`), a non-placeholder
   latest price, source labeled **XT**, and a last-update time after load/refresh.
4. Confirm an explicit **Refresh** control updates quote and/or history or shows
   a clear failure/STALE state — never invented numbers.
5. **SC-002 timing (manual unless automated):** after a completed successful refresh,
   confirm the Dashboard shows pair, genuine price, XT source, and last-update
   (when available) within **5 seconds** for local use.

**Pass**: SC-001 / SC-002 path without credentials (including manual 5s bound unless covered by an automated test).

### 2. Searchable USDT pairs + favorites (P1)

1. Open pair selector; search (e.g. `eth`).
2. Confirm listed pairs are USDT-quoted only.
3. Favorite a pair; reload Dashboard; favorite appears **before** the full list.
4. Confirm Auto Trading / Portfolio remain placeholders with **no** portfolio or
   trading state created by the favorite.

**Pass**: FR-018/FR-019 / SC-009.

### 3. Intervals and history (P2)

1. With a liquid pair selected, view candlestick/history.
2. Switch among `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.
3. Confirm default interval is `1h` on first visit (no prefs).
4. Confirm reload restores last pair + interval when still valid.

**Pass**: SC-004 / FR-005 / FR-018.

### 4. Fail-safe and STALE (P1)

1. Stop backend or block XT (e.g. disconnect network after a successful load) and
   refresh — clear unavailable/error; no fabricated price.
2. After a successful **quote** load, wait **>60 seconds** without refresh —
   last-known price/stats may remain but MUST show **STALE**, not fresh/current.
   Staleness is based on quote `observedAt` / `retrievedAt`, **not** candle
   `openTime`.
3. Confirm `GET /health` success is still distinguishable from market-data
   failure when both are observable.

**Pass**: SC-005 / FR-008 / FR-009.

### 5. Race-safe selection

1. Quickly switch pairs (and intervals) several times.
2. Confirm the UI settles on the **latest** selection’s data (or its loading/error
   state), not an older response labeled as the new pair/interval.

**Pass**: Spec edge cases for rapid pair/interval changes.

### 6. Phone-width (P2)

1. Resize to ~375px width.
2. Confirm pair control, price or error status, source/status, refresh, and
   simple history remain usable/readable.

**Pass**: SC-006 / FR-012.

### 7. Adapter isolation (review)

1. Search frontend for `sapi.xt.com` and XT short keys (`"cr"`, raw envelopes):
   expect **no** matches in Dashboard presentation code.
2. Confirm XT HTTP calls live under `backend/app/market_data/adapters/`.

**Pass**: SC-007 / FR-010.

### 8. Out of scope remains unimplemented (review)

Confirm no trading, simulation, risk, strategies, portfolio calculations,
sentiment/news, auth, WebSockets, futures/margin/leverage, or SQL preference
store shipped for this feature. Confirm Feature 002 can be accepted with
**manual refresh only** (auto-refresh absent or unfinished is OK).

**Pass**: SC-008 / FR-014–FR-017.

## Contract smoke (optional curl)

With backend running:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/market/pairs | head
curl -sS "http://127.0.0.1:8000/market/quote?symbol=btc_usdt"
curl -sS "http://127.0.0.1:8000/market/candles?symbol=btc_usdt&interval=1h&limit=3"
```

Expect JSON matching [contracts/market-data.md](./contracts/market-data.md), not
raw XT envelopes.
