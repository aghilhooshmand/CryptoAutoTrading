import { describe, expect, it } from "vitest";
import {
  XT_SPOT_FEE_RATE,
  percentPointsToRate,
  rateToPercentPoints,
  rateToUsdtAmount,
  usdtAmountToRate,
} from "../services/tradingCosts";

describe("trading cost money ↔ rate conversion", () => {
  it("uses XT VIP0 0.20% as default fee fraction", () => {
    expect(XT_SPOT_FEE_RATE).toBe("0.002");
  });

  it("converts $2 fee on $500 max position to 0.4%", () => {
    expect(usdtAmountToRate("2", "500")).toBe("0.004");
    expect(rateToUsdtAmount("0.004", "500")).toBe("2");
  });

  it("converts XT default fee on $100 max position to $0.20", () => {
    expect(rateToUsdtAmount(XT_SPOT_FEE_RATE, "100")).toBe("0.2");
  });

  it("converts percent points to fraction rate and back", () => {
    expect(percentPointsToRate("0.20")).toBe("0.002");
    expect(rateToPercentPoints("0.002")).toBe("0.2");
    expect(percentPointsToRate("0.211")).toBe("0.00211");
  });
});
