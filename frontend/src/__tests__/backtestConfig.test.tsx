import { describe, expect, it } from "vitest";
import { validateCapitalNesting } from "../services/backtestApi";

describe("backtest config validation", () => {
  it("accepts valid nesting", () => {
    expect(validateCapitalNesting("1000", "500", "500")).toBeNull();
  });

  it("rejects broken nesting", () => {
    expect(validateCapitalNesting("100", "500", "500")).not.toBeNull();
  });
});
