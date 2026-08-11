import { describe, expect, it } from "vitest";
import {
  MAX_BACKTEST_CANDLES,
  estimateCandleCount,
  oversizedHistoryMessage,
  validateCapitalNesting,
} from "../services/backtestApi";

describe("backtest config validation", () => {
  it("accepts valid nesting", () => {
    expect(validateCapitalNesting("1000", "500", "500")).toBeNull();
  });

  it("rejects broken nesting", () => {
    expect(validateCapitalNesting("100", "500", "500")).not.toBeNull();
  });

  it("estimates 1m candles and flags multi-month windows as oversized", () => {
    const start = Date.parse("2026-05-11T17:41:00");
    const end = Date.parse("2026-08-11T17:42:00");
    const n = estimateCandleCount(start, end, "1m");
    expect(n).toBeGreaterThan(MAX_BACKTEST_CANDLES);
    expect(oversizedHistoryMessage(n, "1m")).toMatch(/max 5000/i);
    expect(oversizedHistoryMessage(n, "1m")).toMatch(/1m/i);
  });

  it("keeps a short 1h window under the cap", () => {
    const start = Date.parse("2026-08-01T00:00:00");
    const end = Date.parse("2026-08-07T00:00:00");
    expect(estimateCandleCount(start, end, "1h")).toBeLessThanOrEqual(
      MAX_BACKTEST_CANDLES,
    );
  });
});
