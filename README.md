# CryptoAutoTrading

Responsive cryptocurrency auto-trading platform.

Feature `001-app-foundation` provides the local shell (three primary areas +
health). Feature `002-xt-market-data` adds public XT Spot market data on the
Dashboard (USDT pairs, quote, history). Feature `003-simulation-trading-core`
adds simulation-only Auto Trading (dual EMA, journals, hard stops). Feature
`004-backtesting-core` adds historical Dual EMA backtests under the same Auto
Trading page (offline evaluation, no real orders). Feature
`005-strategy-framework` makes strategies selectable (registry + Dual EMA
canonical id `dual_ema`, editable periods defaulting to 9/21) for Simulation
and Backtest. Feature `006-additional-strategies` adds RSI, MACD, Bollinger
Bands, and Breakout on the same registry (five strategies total). Feature
`007-strategy-comparison` adds fair multi-strategy comparison under Auto
Trading (shared candles, 2–5 legs, no automatic winner). Feature
`008-trading-experiment-defaults` centralizes reusable operator defaults.
Feature `009-portfolio-capital-allocation` adds the **Simulation Portfolio**
(fund USDT, fill-driven holdings, public valuation, compact capital
reservation). Real-money trading, sentiment, and auth remain out of scope.

## Prerequisites

- **Python 3.12** (project target; `>=3.12` may work for local development)
- **Node.js LTS** (includes npm)
- Network access to `https://sapi.xt.com` for live market data
- **Public market data needs no XT credentials**
- **Optional (Feature 013)**: `XT_API_KEY` and `XT_API_SECRET` for read-only Real XT
  account inspect (`/portfolio/real-xt`). Use a **read-scoped** key without withdrawal
  permission. Never commit real secrets. See `.env.example` and
  [`specs/013-xt-account-private-api/quickstart.md`](specs/013-xt-account-private-api/quickstart.md).

## Canonical routes

| Area | Path | Nav icon |
|------|------|----------|
| Dashboard (default) | `/dashboard` | LayoutDashboard |
| Auto Trading | `/auto-trading` | Bot |
| Portfolio | `/portfolio` | Wallet |

Opening `/` resolves to Dashboard (`/dashboard`).

Unsupported paths show a dedicated **Not Found** page with primary navigation
still available (no silent redirect).

**Real XT Account** (Feature 013) is a read-only sub-route under Portfolio:
`/portfolio/real-xt` — not a fourth primary nav item; separate from Simulation Portfolio.

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

Vite proxies `/health`, `/market`, `/simulation`, `/backtest`, `/strategies`,
`/comparisons`, `/settings`, `/portfolio`, and `/xt-account` to the backend.
Open the frontend URL and use Dashboard **Refresh** to load XT public market data
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

### Live paper-trading hardening (Feature 014)

Long-running Simulation sessions use **conditional safe auto-recovery** after a
backend restart: trading resumes only when full ledger reconciliation passes and
offline closed candles are skipped (watermark advanced, gap audited). Otherwise
the session enters non-trading **`RECOVERY_BLOCKED`** (distinct from History
`STOPPED`). Operators may **Resume** (re-checks gates) or stop / start a new
session. No Real trading or XT private credentials are required for paper trading.

Feature 014 validation guide:
[`specs/014-live-paper-trading-hardening/quickstart.md`](specs/014-live-paper-trading-hardening/quickstart.md)

### Stage-1 trading gap-close (Feature 025)

Optional per-position **take-profit / stop-loss percentages** on Simulation and
Backtest creates. Absolute levels are derived from the entry fill; triggers use
candle high/low (never the entry-fill candle). Fills stay mode-native —
Simulation live mark vs Backtest next-open — and never use the TP/SL price.
Protective exits do not consume `maxTrades`. No Real trading.

Semantics (intentional Sim vs Backtest differences):
[`specs/025-stage1-trading-gap-close/contracts/sim-vs-backtest-semantics.md`](specs/025-stage1-trading-gap-close/contracts/sim-vs-backtest-semantics.md)

## Historical backtesting (Feature 004)

Offline Dual EMA backtests also live under **Auto Trading** (no fourth primary
nav). Runs are synchronous, use public historical candles only, and do not place
real orders or mutate a live simulation session.

- Hard cap: **`MAX_BACKTEST_CANDLES = 5000`** (oversized windows are rejected
  before fetch)
- Optional DB path: `BACKTEST_DB_PATH` (defaults beside the simulation DB under
  `backend/data/`)
- Retention: up to **20** completed and **5** failed runs (FIFO)

```bash
# With backend + frontend running:
# open http://127.0.0.1:5173/auto-trading  → Historical backtest section
curl -sS http://127.0.0.1:8000/backtest/runs
```

Feature 004 validation guide:
[`specs/004-backtesting-core/quickstart.md`](specs/004-backtesting-core/quickstart.md)

## Strategy selection (Feature 005 / 006)

Simulation and Backtest share a strategy registry. Operators choose among
**Dual EMA**, **RSI**, **MACD**, **Bollinger Bands**, and **Breakout** under
Auto Trading; `strategyId` is required on create. Dual EMA defaults remain fast
9 / slow 21. See
[`specs/005-strategy-framework/quickstart.md`](specs/005-strategy-framework/quickstart.md)
and
[`specs/006-additional-strategies/quickstart.md`](specs/006-additional-strategies/quickstart.md).

```bash
curl -sS http://127.0.0.1:8000/strategies
```

Expected: five registered strategies when Feature 006 is complete.

## Strategy comparison (Feature 007)

Compare **2–5** registered strategies on one shared historical window under
**Auto Trading → Comparison**. One candle fetch; each leg is a normal backtest
run marked `origin=comparison` (hidden from default backtest history). No
automatic “best/winner” label. Retention: **10** completed + **5** failed
comparisons (FIFO).

```bash
# open http://127.0.0.1:5173/auto-trading → Comparison tab
curl -sS http://127.0.0.1:8000/comparisons
```

Feature 007 validation guide:
[`specs/007-strategy-comparison/quickstart.md`](specs/007-strategy-comparison/quickstart.md)

## Trading defaults (Feature 008)

Reusable operator defaults live under **Auto Trading → Settings** (not a fourth
primary nav). Explicit Save / Reset; defaults only seed **fresh** Simulation,
Backtest, and Comparison forms (comparison: first strategy leg only). Changing
Settings never rewrites historical runs or starts trading.

```bash
# open http://127.0.0.1:5173/auto-trading → Settings tab
curl -sS http://127.0.0.1:8000/settings
```

Feature 008 validation guide:
[`specs/008-trading-experiment-defaults/quickstart.md`](specs/008-trading-experiment-defaults/quickstart.md)

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
streaming, multi-session concurrency, news / Fear & Greed sentiment,
futures/margin/leverage, authentication, or a Real XT Portfolio (Feature 013).
Feature 009 provides the **Simulation Portfolio** only (simulation USDT funding,
fill-driven holdings, public mark-to-market — not live exchange balances).
