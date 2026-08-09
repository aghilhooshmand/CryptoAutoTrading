/** Quote freshness helpers (Dashboard STALE is quote-timed only). */

const STALE_MS = 60_000;

export function quoteReferenceTime(quote: {
  observedAt?: string | null;
  retrievedAt?: string | null;
}): number | null {
  const raw = quote.observedAt || quote.retrievedAt;
  if (!raw) return null;
  const ms = Date.parse(raw);
  return Number.isFinite(ms) ? ms : null;
}

export function isQuoteStale(
  quote: { observedAt?: string | null; retrievedAt?: string | null },
  nowMs: number = Date.now(),
): boolean {
  const ref = quoteReferenceTime(quote);
  if (ref == null) return true;
  return nowMs - ref >= STALE_MS;
}

export function displayMarketStatus(
  base: string,
  quote: { observedAt?: string | null; retrievedAt?: string | null } | null,
  nowMs: number = Date.now(),
): string {
  if (!quote) return base;
  if (base === "loading" || base === "error" || base === "unavailable" || base === "unsupported") {
    return base;
  }
  return isQuoteStale(quote, nowMs) ? "stale" : "fresh";
}
