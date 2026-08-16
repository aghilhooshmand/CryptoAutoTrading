# Contract: Public Market-Data Retry (Simulation)

**Feature**: `014-live-paper-trading-hardening`  
**Date**: 2026-08-16  
**Consumer**: Simulation mark / candle / offline-gap history fetches via public XT  
**Non-goals**: Private XT trading; inventing quotes; unbounded loops

Implements FR-012 / research **R5**. Applies to **public** market-data reads
only (Feature 002 adapter path), not Feature 013 private account client.

---

## Policy

| Parameter | Value |
|-----------|--------|
| Max automatic retries | 1 (at most one re-attempt after the first failure) |
| Default backoff | 0.5 seconds when no usable `Retry-After` |
| Max `Retry-After` wait | 2.0 seconds |
| If `Retry-After` > 2.0s | Do **not** retry; return failure immediately |
| Eligible for retry | Timeout, connection error, HTTP 5xx, transient retryable adapter errors; HTTP 429 when wait ≤ 2.0s |
| Not eligible | Other HTTP 4xx, permanent contract/parse failures after first response |

After exhaustion, caller receives failure. Simulation MUST treat as
untrustworthy/unavailable mark (increment unsafe streak / fail gap resolve as
specified) — **never invent** a price.

---

## Idempotency with trading

Retries MUST NOT cause a second strategy→execution fill for the same candle.
Watermark / journal idempotency (FR-008/009) remains authoritative even if a
fetch is retried.

---

## Observability

Log at most: attempt count, error class, wait applied, symbol/interval,
session id when known. No secrets (public path has none).

---

## Relation to Feature 013

Private account rate-limit policy (max 1 retry, Retry-After cap 3s) is
**separate**. Do not share private client code paths with Simulation fills.
