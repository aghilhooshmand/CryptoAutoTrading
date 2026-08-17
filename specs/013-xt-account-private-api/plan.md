# Implementation Plan: XT Account / Private API Integration

**Branch**: `013-xt-account-private-api` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified Feature 013 — private signed XT Spot client for **read-only**
account balances, open orders, and order status; env credentials fail-closed;
normalized errors including `timestamp_invalid`; max-one rate-limit retry;
minimal inspect UI at `/portfolio/real-xt` separate from Simulation Portfolio;
**no** place/cancel capability; RealExecutionAdapter remains unavailable; no
operator Real trading mode; public Feature 002 unchanged.

## Summary

Add a dedicated `backend/app/xt_account/` private client (HMAC-SHA256 XT v4
headers) that calls `GET /v4/balances`, `GET /v4/open-order`, and
`GET /v4/order/{orderId}` on `https://sapi.xt.com`, normalizes results with
`real_xt` provenance, and exposes read-only FastAPI routes under
`/xt-account/*`. Credentials come from `XT_API_KEY` / `XT_API_SECRET` only.
Ship a minimal frontend inspect page under the Portfolio primary area that
never accepts secrets or trading actions. Do not wire the private client into
`RealExecutionAdapter` and do not write Feature 009 Portfolio.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript/React (frontend inspect UI)

**Primary Dependencies**: Existing FastAPI + `httpx` (mirror Feature 002 adapter
injectability); React router/AppShell patterns; stdlib `hmac`/`hashlib` for
signing. No new settings framework required.

**Storage**: N/A for Real XT data (read-through). Simulation Portfolio SQLite
unchanged and never written by this feature.

**Testing**: pytest unit (signing vectors, normalizers, error map, rate-limit
bounds, credentials fail-closed) + contract (`TestClient` + fake/mocked private
client); existing `test_real_execution_stub`; Portfolio isolation assertion;
frontend tests only as needed for the new page. No live XT required in CI.

**Target Platform**: Local operator machines (same as Features 002–012)

**Project Type**: Web application (`backend/` + minimal `frontend/` page)

**Performance Goals**: Operator inspect latency; Retry-After wait capped at 3s;
default XT recvWindow 5000 ms; no background polling required in MVP (manual
refresh)

**Constraints**: Spec locks FR-001–FR-017 + clarifications; constitution
XVII–XVIII (public/private + credentials); XIII (no 4th primary nav);
FR-015 unconditional no place/cancel; RealExecutionAdapter stub unchanged for
live fills

**Scale/Scope**: One private client; three read endpoints; one inspect UI route;
six stable error codes; zero trading product paths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | Read-only; fail closed; no invented balances |
| II Simulation before real money | Pass | No live trading path |
| III Single trading pipeline | Pass | No second engine; private client not strategy-callable for trades |
| IV Controller / Risk authority | Pass | Strategies still must not call private trading APIs; 013 adds account reads only |
| V Explicit boundaries | Pass | Spot read MVP; futures deferred |
| VI Net P&L | Pass | N/A (no trading economics change) |
| VII Traceability | Pass | Stable error codes for private failures |
| VIII Fail safe | Pass | credentials / auth / timestamp / unavailable fail closed |
| IX Emergency stop | Pass | Unaffected |
| X Intentional simplicity | Pass | Thin private client + minimal UI |
| XII Evidence | Pass | FR-017 test list |
| XIII Primary product areas | Pass | UI under Portfolio sub-route; no 4th nav |
| XIV Operator UI | Pass | Follow UI_UX_STANDARDS; Real vs Simulation labeling |
| XV Stack | Pass | Python + existing frontend |
| XVI Exchange adapters | Pass | Private adapter separate from public |
| XVII Public/private separation | Pass | New `xt_account` package; public client unsigned |
| XVIII Credential safety | Pass | Env only; no frontend secrets; no commit of secrets |
| XXVII–XXXI Process | Pass | Spec clarified; ROADMAP IN PROGRESS |
| XXXII Execution abstraction | Pass | Real stub stays unavailable; no live RealExecutionAdapter |
| XXXIV Portfolio | Pass | Explicit isolation from Feature 009 |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design keeps public `market_data` independent; private reads only under
`xt_account`; UI is inspect-only under Portfolio; no place/cancel methods;
RealExecutionAdapter not connected to XT; Simulation Portfolio has no write
path from Real XT. Deferred concrete XT field edge cases are covered by
normalization rules (omit untrustworthy invented fields).

## Project Structure

### Documentation (this feature)

```text
specs/013-xt-account-private-api/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── xt-account-api.md
│   └── xt-private-signing.md
├── spec.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks — not created by this command
```

### Source Code (repository root)

```text
backend/app/
├── xt_account/
│   ├── __init__.py
│   ├── credentials.py      # XT_API_KEY / XT_API_SECRET load + fail-closed
│   ├── signing.py          # HMAC-SHA256 header construction
│   ├── errors.py           # PrivateError / stable codes
│   ├── models.py           # RealXtBalance, orders, snapshots
│   ├── client.py           # XtPrivateClient (httpx, injectable)
│   ├── normalize.py        # balance/order mapping + zero/zero filter
│   └── service.py          # orchestration + rate-limit policy
├── api/
│   └── xt_account.py       # /xt-account/* routes
├── market_data/            # unchanged public XT (Feature 002)
├── portfolio/              # unchanged Simulation book (Feature 009)
└── execution/real.py       # unchanged unavailable stub (Feature 012)

frontend/src/
├── pages/RealXtAccountPage.tsx          # /portfolio/real-xt
├── features/xt-account/                 # panels: balances, open orders, status lookup
├── services/xtAccountApi.ts
└── App.tsx                              # route registration; link from Portfolio

backend/tests/
├── unit/test_xt_account_signing.py
├── unit/test_xt_account_normalize.py
├── unit/test_xt_account_errors_rate_limit.py
├── unit/test_xt_account_portfolio_isolation.py
└── contract/test_xt_account_api.py
```

**Structure Decision**: Web app with a new private-account backend package
parallel to `market_data`, plus one Portfolio-area inspect page. No DB schema.

## Complexity Tracking

> No constitution violations requiring justification.

---

## Amendment 2026-08-17 — Kraken private-read plan

**Gate**: Feature 002 Kraken public (FR-021–FR-038) is complete
(`feat: add Kraken-first public market data and product identity`).
Implement this amendment now. Do not add Kraken place/cancel.

**Summary**: Venue-neutral private-account port + Kraken adapter. XT package
remains. No place/cancel. No RealExecutionAdapter writes. Simulation
Portfolio isolation unchanged.

**Constitution**: XVI–XVIII, IV, XXXIX PASS (read-only, credentials, isolation).

**Additive paths**:

```text
backend/app/account/port.py              # venue-neutral protocol (name may vary)
backend/app/account/kraken_private.py    # Kraken adapter only
# keep backend/app/xt_account/ for regression
frontend Real Account UI (Kraken labeling); legacy real-xt may remain
.env.example KRAKEN_API_KEY / KRAKEN_API_SECRET placeholders
```
