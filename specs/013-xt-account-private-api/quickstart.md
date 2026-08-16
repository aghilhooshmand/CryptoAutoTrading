# Quickstart: Feature 013 — XT Account / Private API

**Date**: 2026-08-16  
**Goal**: Validate read-only Real XT account integration locally without enabling trading.

See also: [contracts/xt-account-api.md](./contracts/xt-account-api.md), [data-model.md](./data-model.md), [research.md](./research.md).

---

## Prerequisites

- Branch `013-xt-account-private-api`
- Backend + frontend run as for Features 002/009
- Optional live check: XT Spot API key **without** withdrawal permission
- CI / default validation: **fixtures / mocks only** (no live credentials required)

---

## 1. Credentials (local only)

```bash
export XT_API_KEY="YOUR_API_KEY_HERE"
export XT_API_SECRET="YOUR_API_SECRET_HERE"
```

Unset both to verify fail-closed:

```bash
unset XT_API_KEY XT_API_SECRET
```

Expect `credentials_missing` with HTTP **503** on `/xt-account/balances`.

---

## 2. Automated gates (preferred)

From `backend/`:

```bash
pytest -q \
  tests/unit/test_xt_account_*.py \
  tests/contract/test_xt_account_api.py \
  tests/unit/test_real_execution_stub.py
```

Expect:
- Signing / auth header construction tests pass
- Missing credentials → `credentials_missing`
- `timestamp_invalid` fixture → no account payload; clock not mutated
- Balance normalizer omits zero/zero
- Rate-limit: one retry then `rate_limited`
- Portfolio isolation test: Simulation Portfolio snapshot unchanged
- RealExecutionAdapter still `real_execution_unavailable`
- No place/cancel routes registered under `/xt-account`

Frontend (once UI lands):

```bash
# from frontend/
npm test -- --run   # or project’s equivalent for new Real XT page tests if added
```

---

## 3. Manual UI check (after implement)

1. Start backend + frontend.
2. Open Simulation Portfolio (`/portfolio`) — confirm familiar simulation book.
3. Open **Real XT Account** (`/portfolio/real-xt`).
4. Confirm labeling shows real XT provenance; **no** place/cancel/trade controls.
5. With credentials unset: error shows `credentials_missing`.
6. With valid credentials (optional): balances / open orders load; empty lists OK.
7. Order lookup: known id → status; unknown → `order_not_found`.
8. Re-check `/portfolio` — simulation numbers unchanged.

---

## 4. Safety checklist

| Check | Expected |
|-------|----------|
| Public `/market/*` | Works without XT private env |
| `/portfolio` | Unchanged book; provenance `simulation` |
| `/xt-account/*` | provenance `real_xt` only |
| RealExecutionAdapter.execute | `real_execution_unavailable` |
| Place/cancel | Not present |

---

## 5. Out of scope for this quickstart

- Live order placement or cancel
- Operator Real trading mode
- Feature 014 hardening / 015 confirmation UX
