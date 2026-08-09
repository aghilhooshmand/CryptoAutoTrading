# Quickstart: Application Foundation

**Feature**: `001-app-foundation`  
**Date**: 2026-08-08

Validate that a developer can run the app locally, navigate the three primary
areas on desktop and phone-width viewports, and verify backend health.
    
## Prerequisites
 
- Documented toolchain installed (see root `README.md` after implementation):
  Python 3.12, Node.js LTS, package managers as documented
- No XT.COM credentials or exchange setup required

## Start locally

Follow root `README.md` to:

1. Start the backend
2. Start the frontend
3. Open the frontend URL in a browser

Expected: product shell loads without trading credentials.

## Scenario A — Default entry (SC-002 / FR-002)

1. Open `/` (application root).
2. Confirm it resolves to **Dashboard** (canonical path `/dashboard`).
3. Confirm the active area is **Dashboard** and CryptoAutoTrading product shell identity is visible.

## Scenario B — Navigate three areas (SC-002 / FR-002–FR-005)

Canonical primary routes: `/dashboard`, `/auto-trading`, `/portfolio`.

1. Select **Auto Trading** via primary navigation (path `/auto-trading`) →
   placeholder only; no strategies, sessions, or trades.
2. Select **Portfolio** (path `/portfolio`) → placeholder only; no balances,
   positions, or P&L.
3. Select **Dashboard** (path `/dashboard`) → placeholder only; no market, news,
   or sentiment data.
4. Confirm the active area is visually indicated after each switch.

## Scenario C — Phone-width navigation (SC-003 / FR-006)

1. Resize viewport to ~375px width (or use device emulation).
2. Complete navigation to all three primary areas.
3. Confirm controls remain reachable and labels/titles remain readable.

## Scenario D — Backend health (SC-004 / FR-007)

With backend running, request health per [contracts/health.md](./contracts/health.md):

```bash
curl -sS http://localhost:<backend-port>/health
```

Expected: HTTP 200 and JSON including `"status":"healthy"` in under 2 seconds.

## Scenario E — Health failure (SC-005 / FR-008)

1. Stop the backend.
2. Repeat the health request.
3. Expected: failure/unreachable — not a healthy success.

## Scenario F — Unknown location (FR-012)

1. Open a path that is not a primary area (e.g., `/this-is-not-a-page`).
2. Expected: clear not-found experience with primary navigation still available.
3. Navigate from there to `/dashboard` (or another primary area) successfully.

## Scenario G — Deep link / refresh

1. Open each canonical path directly: `/dashboard`, `/auto-trading`, `/portfolio`.
2. Refresh the browser on each.
3. Expected: same primary area placeholder, with navigation intact.

## Scenario H — Scope guard (SC-006 / SC-007 / FR-010–FR-011)

Visual pass: zero live or mocked trading, portfolio P&L, market prices, news,
or sentiment presented as real data. No Google auth, exchange, or backtesting
UI.

## Automated checks (after implementation)

- Backend: pytest contract tests for `GET /health`
- Frontend: Vitest/RTL tests for routes, default Dashboard, placeholders, and
  not-found recovery

Exact commands will live in root `README.md` / package scripts once implemented.
