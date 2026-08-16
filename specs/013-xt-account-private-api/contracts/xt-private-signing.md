# Contract: XT private signing & error mapping

**Feature**: `013-xt-account-private-api`  
**Date**: 2026-08-16  
**Purpose**: Lock signing and error-normalization behavior for implementers/tests (complements `xt-account-api.md`).

---

## Signing algorithm (normative for 013)

1. Build validate headers: `algorithms=HmacSHA256`, `appkey`, `recvwindow` (default `"5000"`), `timestamp` (ms string).
2. `X` = sorted `key=value` joined by `&` for those four headers (keys prefixed `validate-` in the wire headers; signing uses the XT documented header-name form).
3. `Y` = `#` + `METHOD` + `#` + `path` + optional `#query` + optional `#body` per XT `signSteps` (omit empty query/body segments).
4. `signature = HMAC_SHA256_HEX(secret, X + Y)`.
5. Send headers: `validate-algorithms`, `validate-appkey`, `validate-recvwindow`, `validate-timestamp`, `validate-signature`.

Tests MUST cover deterministic signature for a fixed timestamp/key/path/query fixture.

---

## XT `mc` → stable code (minimum map)

| XT `mc` / signal | Stable code |
|------------------|-------------|
| (missing env credentials) | `credentials_missing` |
| `AUTH_101`, `AUTH_102`, `AUTH_103`, `AUTH_104`, `AUTH_106`, `AUTH_001`–`AUTH_007` (except pure timestamp cases) | `authentication_failed` |
| `AUTH_105`; docs “outdated message”; client ahead of server / outside recvWindow when identifiable | `timestamp_invalid` |
| HTTP 429 | rate-limit handler → eventually `rate_limited` |
| `ORDER_005` | `order_not_found` |
| HTTP 5xx, timeout, malformed JSON/envelope, unknown `mc` | `xt_private_unavailable` (or more specific map if clearly auth) |

`timestamp_invalid` message SHOULD mention clock skew / timestamp / NTP for operators. Never mutate system clock.

---

## Rate-limit handler (normative)

```text
on 429:
  if already_retried: return rate_limited
  delay = parse Retry-After or SHORT_BACKOFF (0.5s)
  if delay > 3.0s: return rate_limited  # no wait, no retry
  sleep(delay)
  retry once
  if 429 again: return rate_limited
```

---

## Non-goals

- Withdrawal / transfer endpoints
- Place / cancel order APIs
- Auto clock sync against XT server time in 013 (may be reconsidered in later hardening features if needed)
