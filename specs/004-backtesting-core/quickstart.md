# Quickstart: Backtesting Core

**Feature**: `004-backtesting-core`  
**Date**: 2026-08-11

Validate Feature 004 locally without exchange trading credentials. Historical
candles still use public XT via Feature 002. Backtesting never places real
orders and must not mutate a live simulation session.

For API shapes see [contracts/backtest-api.md](./contracts/backtest-api.md).  
For entities and fill rules see [data-model.md](./data-model.md) and
[research.md](./research.md).

---

## Prerequisites

- Tools already installed from Features 001–003 (Python 3.12+, Node, npm)
- Backend and frontend deps installed
- No XT API keys / trading credentials
- Feature 003 Dual EMA simulation path available (shared strategy module)

---

## Setup

From repo root:

```bash
# Backend
cd backend
source .venv/bin/activate   # or create venv + pip install -e ".[dev]"
mkdir -p data
export SIMULATION_DB_PATH="${SIMULATION_DB_PATH:-$PWD/data/simulation.db}"
# Optional dedicated backtest DB if implemented:
# export BACKTEST_DB_PATH="${BACKTEST_DB_PATH:-$PWD/data/backtest.db}"
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
- Vite proxies `/backtest` to the backend (configured in implementation)

---

## Manual validation scenarios

### 1. Configure and complete one backtest (SC-001, US1)

1. Open `http://127.0.0.1:5173/auto-trading`.
2. Find **Backtest** (section/tab) — distinct from live **Simulation**; no
   fourth primary nav item.
3. Configure: symbol (e.g. `btc_usdt`), timeframe (`1h` or `15m`), start/end
   within documented max (**≤ 5000** closed candles — see research Decision 4),
   starting / allocated / max position capital nesting, fee/slippage (or
   defaults), optional max trades and optional profit/loss rates.
4. Run → completed summary with starting/ending capital, net P&L, return %.

**Expect**: Invalid nesting, end ≤ start, unsupported TF, or oversized window
blocked with a clear reason and **no** stored run (no silent truncate). Empty
or fewer-than-21 closed-candle windows fail with `insufficient_history` (durable
`failed` after accept). Real-money controls remain unavailable.

### 2. Pipeline + next-open fills (SC-002–SC-004, US2)

1. Prefer automated fixture tests for bit-identical determinism.
2. Manually: run a window known to produce HOLD and at least one non-HOLD.
3. Inspect decisions: HOLD does not change balances; risk **rejections** show
   `outcome: rejected`; approved orders with no next candle show
   `approved_unexecutable` / `no_next_candle` (not rejected); successful
   fills use next-open via the historical execution adapter.

**Expect**: Strategy never writes balances directly; controller/risk visible in
decision outcomes.

### 3. Metrics, trades, persistence (SC-005, SC-005a, US3)

1. Open trades: each fill shows side, sizes, prices/costs, strategy vs
   end-of-run flatten.
2. Summary includes win/loss (round-trips), fees, slippage, max drawdown,
   best/worst, buy-and-hold (**window-based**, not delayed for EMA warm-up).
3. Restart backend; reopen the same run id — config, summary, trades, decisions
   still present (≤20 completed; ≤5 failed if applicable).
4. Create enough completed runs to exceed 20 → oldest completed disappears.
5. Create enough persisted failures to exceed 5 → oldest failed disappears.
6. Delete one run → gone from list and get-by-id.

### 4. Isolation from simulation (edge)

1. Start a Feature 003 simulation session (optional).
2. Run a backtest while it is active.
3. Confirm simulation cash/position unchanged by the backtest.

### 5. Phone-width UX (SC-009, US4)

At ~375px width, complete configure → run → summary → trades without
desktop-only gestures for primary controls.

---

## Automated checks (after implementation)

```bash
cd backend
pytest tests/unit/test_backtest_*.py tests/contract/test_backtest_api.py \
  tests/integration/test_backtest_pipeline.py -q

cd ../frontend
npm test -- --run
```

**Expect**:

- Determinism: identical fixture config + candles → identical decimal strings
  and trade lists (SC-002).
- Oversized window → `oversized_history` before accept; **no** BacktestRun row
  (SC-006a).
- Empty or fewer-than-21 closed candles → `insufficient_history`; zero
  fabricated candles (SC-006).

---

## Out of scope (must remain absent)

Additional strategies, optimization/grid search, WebSockets, real money,
private XT trading APIs, shorts/leverage, sentiment, fourth primary nav.
