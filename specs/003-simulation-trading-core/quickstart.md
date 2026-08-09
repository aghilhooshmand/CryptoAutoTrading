# Quickstart: Simulation Trading Core

**Feature**: `003-simulation-trading-core`  
**Date**: 2026-08-09

Validate Feature 003 locally without exchange trading credentials. Market data
still uses public XT via Feature 002. Simulation never places real orders.

For API shapes see [contracts/simulation-api.md](./contracts/simulation-api.md).  
For accounting and state rules see [research.md](./research.md) and
[data-model.md](./data-model.md).

---

## Prerequisites

- Tools already installed from Features 001–002 (Python 3.12+, Node, npm)
- Backend and frontend deps installed
- No XT API keys

---

## Setup

From repo root:

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# After Feature 003 deps land: SQLAlchemy comes from pyproject

export SIMULATION_DB_PATH="${SIMULATION_DB_PATH:-$PWD/data/simulation.db}"
mkdir -p data
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# Frontend (other terminal)
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Confirm:

- `GET http://127.0.0.1:8000/health` → ok  
- `GET http://127.0.0.1:8000/market/pairs` → Feature 002 still works  
- Vite proxies `/simulation` to the backend (configured in implementation)

---

## Manual validation scenarios

### 1. Configure and start one simulation session (SC-001, US1)

1. Open `http://127.0.0.1:5173/auto-trading`.
2. Confirm a clear **SIMULATION** label; real-money controls unavailable.
3. Configure: symbol (e.g. `btc_usdt`), capital, max position size, profit
   target, max loss, max trades, duration, timeframe (`1h` recommended for
   demos — or `15m` for faster closes).
4. Leave fee/slippage blank → defaults **0.10%** / **0.05%** apply.
5. Start session → state `RUNNING`; only one active session allowed.

**Expect**: Second start while active fails with a clear conflict.

### 2. Pipeline authority (SC-002, US2)

1. With session running, wait for at least one **closed** candle evaluation
   (use FakeClock in automated tests; manually, shorter timeframe helps).
2. Observe Decision Journal entries for `HOLD` and any `BUY`/`SELL`.
3. Confirm no balance change on `HOLD`; any fill appears in Trade Journal and
   only after approval path (no strategy-only mutation).

**Expect**: Rejected invalid position-state signals (BUY while long, SELL while
flat) appear in Decision Journal with reasons and do not change cash.

### 3. Economics and journals (SC-003, SC-004, US3)

1. After ≥1 rejection and ≥1 fill (or forced close in a later scenario), open
   Decision Journal and Trade Journal.
2. Economics show distinct `grossPnl`, `fees`, `slippageCost`, `netPnl`.

**Expect**: 100% of observed rejects/fills are listed per success criteria.

### 4. Hard stop + forced close (SC-005, US4)

1. Configure a tiny `targetNetProfit` or `maxSessionLoss` / short
   `durationSeconds` / `maxTrades: 1`.
2. Run until stop fires. Profit/max-loss use **liquidation** Session NET while
   LONG (hypothetical adverse SELL with fee/slippage), not raw mark equity.
3. If long and quote safe → one forced full `SELL` in Trade Journal with
   `isForcedClose: true`; `positionFlattenStatus` forced/flat. Actual exit
   costs apply once (no double-count of the hypothetical evaluation).
4. If stop with unsafe mark (simulate stale in tests) → no invented exit;
   `unsafe_unflattened`.
5. With `maxTrades` exhausted while LONG: strategy fills stop; one forced
   close may still run so `tradeCount` can be `maxTrades + 1`.

**Expect**: No further strategy-driven simulated executions in that session
after `STOPPED`.

### 5. Fail-safe market data (SC-006)

1. In tests, inject stale/missing quote into the market-data boundary.
2. Attempt evaluation/execution.

**Expect**: Reject/suspend; zero fabricated prices.

### 6. Backend restart recovery

1. Start a session (`RUNNING`), optionally leave a long open.
2. Restart uvicorn.
3. Query active session / previous id.

**Expect**: Prior session `STOPPED` with `stopReason: backend_restart`; not
resumed; if it was long, `unsafe_unflattened`; no silent new fills from the
old session.

### 7. Phone-width UX (SC-009)

1. Resize to ~375px on Auto Trading.
2. Configure/start/status/stop/emergency-stop remain usable; simulation label
   visible.

---

## Automated checks (after implementation)

```bash
cd backend && pytest
cd frontend && npm test
```

Priority backend suites: accounting (liquidation vs mark; no double-count),
dual EMA, duplicate candle, state machine, risk rejects, max_trades + forced
close, recovery, simulation API contract, pipeline integration with `FakeClock`
+ fake market data.

---

## Out of scope reminders

Do not expect: real orders, XT private APIs, WebSockets, shorts, multi-session,
multi-strategy, backtesting, sentiment, or production deployment.
