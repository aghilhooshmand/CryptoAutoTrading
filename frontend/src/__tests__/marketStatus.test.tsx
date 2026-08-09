import { describe, expect, it } from "vitest";

import { displayMarketStatus, isQuoteStale } from "../features/market-data/freshness";

describe("market status freshness", () => {
  it("marks quote stale after 60s using observedAt, not candle openTime", () => {
    const observedAt = "2026-08-09T16:00:00.000Z";
    const now = Date.parse(observedAt) + 61_000;
    expect(
      isQuoteStale({ observedAt, retrievedAt: "2026-08-09T16:00:01.000Z" }, now),
    ).toBe(true);
    expect(
      displayMarketStatus("fresh", { observedAt }, now),
    ).toBe("stale");
  });

  it("keeps fresh within 60s and does not use candle openTime", () => {
    const observedAt = "2026-08-09T16:00:00.000Z";
    const now = Date.parse(observedAt) + 10_000;
    // Candle openTime from hours ago must not matter — freshness helper only sees quote times.
    expect(isQuoteStale({ observedAt }, now)).toBe(false);
    expect(displayMarketStatus("fresh", { observedAt }, now)).toBe("fresh");
  });

  it("falls back to retrievedAt when observedAt missing", () => {
    const retrievedAt = "2026-08-09T16:00:00.000Z";
    const now = Date.parse(retrievedAt) + 61_000;
    expect(isQuoteStale({ retrievedAt }, now)).toBe(true);
  });
});
