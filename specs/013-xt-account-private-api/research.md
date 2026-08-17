# Research: Feature 013 — XT Account / Private API

**Date**: 2026-08-16  
**Branch**: `013-xt-account-private-api`  
**Sources**: Clarified `spec.md`; XT Spot docs ([XtApis/xt-api](https://github.com/XtApis/xt-api)); existing Feature 002/009/012 code; constitution XVII–XVIII, XIII–XIV.

---

## R1 — Private client package layout

**Decision**: New package `backend/app/xt_account/` (private-only), separate from `backend/app/market_data/`. HTTP routes in `backend/app/api/xt_account.py`. Do **not** extend `XtSpotAdapter`.

**Rationale**: Constitution XVII requires public vs private separation. Feature 002 `XtSpotAdapter` is unsigned public GETs only; mixing signing/credentials into it would violate fail-closed credential boundaries and FR-001/FR-016.

**Alternatives considered**:
- Extend `XtSpotAdapter` with optional credentials — rejected (blurs public/private).
- Nest under `execution/` — rejected (013 is account read, not fill execution; RealExecutionAdapter stays stub).

---

## R2 — XT Spot endpoints (read-only MVP)

**Decision**: Bind to current XT Spot private REST on `https://sapi.xt.com` (same host as public market data, different signed paths):

| Capability | Method | Path |
|------------|--------|------|
| Balances | GET | `/v4/balances` |
| Open orders | GET | `/v4/open-order` |
| Order status | GET | `/v4/order/{orderId}` |

Optional filter later: `GET /v4/balance?currency=` is out of MVP (list endpoint covers FR-005).

**Field mapping (XT → normalized)**:
- Balance: `currency` → asset; `availableAmount` → free/available; `frozenAmount` → locked; `totalAmount` → total when present (else free+locked when both known).
- Orders: `orderId`, `symbol`, `side`, `origQty` / quantities, `state` → status; provenance always `real_xt`.

**Rationale**: Official XtApis spot Balance/Order docs; envelope matches public (`rc`/`mc`/`result`). Spot-only MVP per Assumptions.

**Alternatives considered**:
- Legacy `/trade/api/v1/*` — rejected (superseded by v4).
- Futures `fapi.xt.com` — deferred (not MVP).

---

## R3 — Signing and timestamp window

**Decision**: Implement XT v4 header signing per official `signSteps` / `signStatement`:

Headers (required):
- `validate-algorithms: HmacSHA256`
- `validate-appkey`
- `validate-timestamp` (ms)
- `validate-recvwindow`
- `validate-signature`

Canonical string: header part `X` (sorted validate-* headers except signature) + data part `Y` (`#METHOD#path#query#body` with omitted empty segments). Signature = HMAC-SHA256 hex of `X+Y` with secret.

Default `validate-recvwindow`: **5000** ms (XT recommendation; >5s discouraged).

Map XT message codes:
- `AUTH_105` (outdated message) and clear recv-window / timestamp skew rejections → **`timestamp_invalid`**
- `AUTH_101`/`102`/`103`/`104`/`106` and missing/bad key style → **`authentication_failed`**
- `ORDER_005` (order not exist) → **`order_not_found`**
- HTTP **429** → rate-limit path (R4)
- HTTP 5xx / transport / malformed envelope → **`xt_private_unavailable`**

Never auto-adjust system clock (FR-010a).

**Rationale**: Spec clarification Option B; XT documents AUTH_105 as outdated message and recvWindow skew rules.

**Alternatives considered**:
- Fold skew into `authentication_failed` — rejected by clarification.
- Use recvWindow 60000 as in some curl samples — rejected for MVP (XT warns against >5s).

---

## R4 — Rate-limit policy (concrete bounds)

**Decision** (implements FR-011):

1. On HTTP 429 (or XT rate-limit signal equivalent): at most **one** automatic retry.
2. Wait: if `Retry-After` present and parseable as seconds (or HTTP-date → delay), wait `min(parsed, MAX_RETRY_AFTER_WAIT_S)`; if parsed wait would exceed max, **do not retry** — return `rate_limited` immediately.
3. If `Retry-After` absent/unusable: wait **SHORT_BACKOFF_S = 0.5**.
4. **MAX_RETRY_AFTER_WAIT_S = 3.0** (keeps inspect UI responsive).
5. After retry still limited (or no retry taken): return `rate_limited`. No loops, no parallel retry storms.

**Rationale**: Clarification Option A + planning note for concrete bound; 3s balances XT 10 req/s/key limits with operator UX.

**Alternatives considered**: No retries (Option B) — clearer but worse UX on transient 429; N=3 exponential — rejected as riskier hammering.

---

## R5 — Credentials configuration

**Decision**:
- Env vars: `XT_API_KEY` (appkey), `XT_API_SECRET` (secret). Both required and non-empty for private ops.
- Load via small `xt_account/credentials.py` reading `os.environ` (matches existing DB env pattern; no new settings framework required).
- Missing/blank → `credentials_missing` before any network call.
- Document placeholders only in README / `.env.example` (never real values).
- Frontend never accepts or displays secrets (FR-012a).

**Rationale**: Constitution XVIII; repo has no pydantic-settings today.

**Alternatives considered**: pydantic-settings module — deferred (unnecessary for two env vars). Frontend secret form — forbidden by FR-012a.

---

## R6 — Operator API + UI placement

**Decision**:
- Backend REST under `/xt-account/*` (balances, open-orders, order-status), JSON camelCase, decimal strings, error envelope `{ "error": { "code", "message" } }` matching market/portfolio style.
- Provenance fields: `bookProvenance: "real_xt"` / `provenance: "real_xt"` — never `"simulation"`.
- UI: sub-route **`/portfolio/real-xt`** (still under Portfolio primary area — no 4th nav item). Distinct page title “Real XT Account”, Real badge, no trading controls; link from Simulation Portfolio page without merging data models or `portfolioApi`.
- Do **not** write Feature 009 tables or call Portfolio apply.

**Rationale**: Clarification Option B; constitution XIII keeps three primary areas; FR-006/007 isolation.

**Alternatives considered**: Auto Trading tab — weaker account semantics; 4th primary nav — violates XIII; merge into Portfolio snapshot — violates FR-007.

---

## R7 — Place/cancel and RealExecutionAdapter

**Decision**: Private client exposes **read methods only** (balances, open orders, order get). No place/cancel methods in 013. `RealExecutionAdapter` remains `real_execution_unavailable` stub; do not inject Xt private client into it.

**Rationale**: Clarification Option A / FR-014/FR-015.

**Alternatives considered**: Internal place/cancel “for tests” — rejected (capability creep toward 015).

---

## R8 — Testing strategy

**Decision**:
- Unit: signing vectors (fixed timestamp/key → known signature from XT demo vectors where applicable); balance/order normalizers (omit zero/zero); error code mapping; rate-limit retry counter (fake clock/sleep).
- Inject `httpx.MockTransport` or injectable async client on private client (mirror `XtSpotAdapter(client=...)`).
- Contract: FastAPI `TestClient` against `/xt-account/*` with fake service (no live XT in CI).
- Isolation: assert Portfolio snapshot unchanged after xt-account reads.
- Safety: assert RealExecutionAdapter still unavailable; assert no place/cancel routes.

**Rationale**: Matches repo patterns (no respx/VCR today); FR-017.

**Alternatives considered**: Live XT in CI — rejected (credentials + flaky).

---

## R9 — Zero balances

**Decision**: After normalizing amounts, omit assets where free and locked are both zero; retain if either > 0; empty list is success.

**Rationale**: Clarification Option A / FR-005.

---

## Resolved Technical Context unknowns

| Topic | Resolution |
|-------|------------|
| XT endpoints | R2 |
| Signing | R3 |
| Retry-After max wait | R4 (3s) |
| Credential env names | R5 |
| UI route | R6 |
| Place/cancel surface | R7 (none) |

## Amendment 2026-08-17 — Kraken private read

**R10 — Layout.** Venue-neutral port in `backend/app/account/` (`port.py`,
models, errors). Kraken signing and REST live only in
`backend/app/account/signing.py` + `kraken_private.py`. Keep
`backend/app/xt_account/` for regression. Do not rename `XtAccountService`.

**R11 — Kraken REST (read-only).** `https://api.kraken.com` POST form body:

| Capability | Path | Notes |
|------------|------|--------|
| Balances | `/0/private/BalanceEx` | `balance` total, `hold_trade` locked; free = total − locked when both present. Fallback `/0/private/Balance` has no split — locked omitted. |
| Open orders | `/0/private/OpenOrders` | Map `open` map keys to `venueOrderId`; `descr.pair` → `venueProductId`. |
| Order status | `/0/private/QueryOrders` | Body `txid=`. Empty result → `order_not_found`. |

No `AddOrder` / `CancelOrder`.

**R12 — Signing.** HMAC-SHA512 of (URI path + SHA256(nonce + POST data)) with
base64-decoded secret; headers `API-Key` / `API-Sign`. Nonce is a strictly
increasing millisecond timestamp. Invalid nonce → `timestamp_invalid`. Never
auto-adjust the host clock. Tests use fixed nonce/secret fixtures, not live
keys.

**R13 — Errors.** Map Kraken `error[]` strings: invalid key/signature →
`authentication_failed`; invalid nonce → `timestamp_invalid`; rate limit /
HTTP 429 → bounded retry then `rate_limited`; unknown order →
`order_not_found`; else `venue_private_unavailable`. Same retry bound as XT
(R4: one retry, Retry-After cap 3s, else 0.5s). Retry MUST use a new nonce.

**R14 — Credentials.** `KRAKEN_API_KEY` / `KRAKEN_API_SECRET`. Fail closed
before network. Placeholders only in `.env.example`. Public Feature 002 does
not read these vars.

**R15 — UI.** Living inspect page `/portfolio/real-account` (Real Account /
Venue: Kraken). Legacy `/portfolio/real-xt` remains. No trading controls.
No secrets in UI. Simulation Portfolio unchanged.
