# CryptoAutoTrading

Responsive cryptocurrency auto-trading platform (foundation stage).

Feature `001-app-foundation` provides a locally runnable shell with three
placeholder primary areas and a backend health capability. Trading, market
data, sentiment, exchange integration, and authentication are intentionally
out of scope.

## Prerequisites

- **Python 3.12** (project target; `>=3.12` may work for local development)
- **Node.js LTS** (includes npm)
- No XT.COM credentials or exchange setup required

## Canonical routes

| Area | Path |
|------|------|
| Dashboard (default) | `/dashboard` |
| Auto Trading | `/auto-trading` |
| Portfolio | `/portfolio` |

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

Open the frontend URL. You should land on **Dashboard** without trading
credentials.

## Backend health

Contract: `specs/001-app-foundation/contracts/health.md`

With the backend running:

```bash
curl -sS -w "\nhttp_code=%{http_code} time=%{time_total}\n" http://127.0.0.1:8000/health
```

Expected: HTTP 200 and JSON `{"status":"healthy"}`. A successful local check
must complete in under **2 seconds** (SC-004).

Feature 001 does **not** require a Dashboard health widget.

### Manual stopped-backend check (SC-005 / FR-008)

1. Stop the backend process.
2. Repeat the `curl` command above.
3. Expected: connection failure / unreachable — not a healthy success.

Do not add infrastructure solely to automate this unreachable-process check.

## Tests

```bash
# Backend contract tests
cd backend
source .venv/bin/activate
pytest

# Frontend navigation / placeholder / not-found / responsive smoke
cd frontend
npm test
```

## Quickstart validation

See `specs/001-app-foundation/quickstart.md` for scenarios A–H, including
phone-width (~375px) navigation checks.

## Out of scope (Feature 001)

Do not expect XT.COM integration, market data, strategies, Trading Controller,
Risk Manager, simulation or real-money trading, portfolio calculations, news,
market sentiment / Fear & Greed indexes, backtesting, AI/ML, Google
authentication, or SQL domain schemas.
