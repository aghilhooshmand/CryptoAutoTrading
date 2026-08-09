# CryptoAutoTrading

Responsive cryptocurrency auto-trading platform.

Feature `001-app-foundation` provides the local shell (three primary areas +
health). Feature `002-xt-market-data` adds public XT Spot market data on the
Dashboard (USDT pairs, quote, history). Feature `003-simulation-trading-core`
adds simulation-only Auto Trading (dual EMA, journals, hard stops). Real-money
trading, sentiment, and auth remain out of scope.

## Prerequisites

- **Python 3.12** (project target; `>=3.12` may work for local development)
- **Node.js LTS** (includes npm)
- Network access to `https://sapi.xt.com` for live market data
- **No XT.COM credentials** (public Spot REST only)

## Canonical routes

| Area | Path | Nav icon |
|------|------|----------|
| Dashboard (default) | `/dashboard` | LayoutDashboard |
| Auto Trading | `/auto-trading` | Bot |
| Portfolio | `/portfolio` | Wallet |

Opening `/` resolves to Dashboard (`/dashboard`).

Unsupported paths show a dedicated **Not Found** page with primary navigation
still available (no silent redirect).

## Start locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL: `http://127.0.0.1:8000`

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173`

Vite proxies `/health`, `/market`, and `/simulation` to the backend. Open the
frontend URL and use Dashboard **Refresh** to load XT public market data
(manual refresh is required; auto-refresh is optional polish and not required).

Feature 002 validation guide:
[`specs/002-xt-market-data/quickstart.md`](specs/002-xt-market-data/quickstart.md)

## Simulation trading (Feature 003)

Local **simulation-only** sessions live under **Auto Trading** (`/auto-trading`).
No XT trading credentials are required. Session state is stored in SQLite
(default `backend/data/simulation.db`, override with `SIMULATION_DB_PATH`).

```bash
# With backend + frontend running:
# open http://127.0.0.1:5173/auto-trading
curl -sS http://127.0.0.1:8000/simulation/sessions/active
```

Feature 003 validation guide:
[`specs/003-simulation-trading-core/quickstart.md`](specs/003-simulation-trading-core/quickstart.md)

## Backend health

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected: HTTP 200 and JSON `{"status":"healthy"}` in under 2 seconds.

## Market data (Feature 002)

Normalized application contracts (not raw XT envelopes):

```bash
curl -sS http://127.0.0.1:8000/market/pairs | head
curl -sS "http://127.0.0.1:8000/market/quote?symbol=btc_usdt"
curl -sS "http://127.0.0.1:8000/market/candles?symbol=btc_usdt&interval=1h&limit=3"
```

Contract: `specs/002-xt-market-data/contracts/market-data.md`

## Tests

```bash
# Backend
cd backend
source .venv/bin/activate
pytest

# Frontend
cd frontend
npm test
```

## Out of scope

Do not expect real-money XT order placement, private XT trading APIs, WebSocket
streaming, multi-session concurrency, multi-strategy selection, news / Fear &
Greed sentiment, futures/margin/leverage, authentication, or a full portfolio
product (Portfolio shows only a thin active-simulation summary).
