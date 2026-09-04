import { describe, expect, it } from "vitest";

import {
  formatMarketAmount,
  formatMarketPercent,
} from "../features/market-data/formatMarketNumber";

describe("formatMarketNumber", () => {
  it("caps long fractional residues used by Change %", () => {
    expect(
      formatMarketPercent("-0.3708398975974793225679401339"),
    ).toBe("-0.37%");
  });

  it("strips trailing zeros from prices and volumes", () => {
    expect(formatMarketAmount("80946.70000")).toBe("80946.7");
    expect(formatMarketAmount("289.68171713")).toBe("289.68171713");
    expect(formatMarketAmount("-301.30000")).toBe("-301.3");
  });

  it("returns null for empty values", () => {
    expect(formatMarketAmount(null)).toBeNull();
    expect(formatMarketPercent(undefined)).toBeNull();
  });
});
