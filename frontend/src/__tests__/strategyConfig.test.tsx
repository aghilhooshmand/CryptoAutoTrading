import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";

import {
  StrategyConfigFields,
  defaultStrategyConfig,
  type StrategyConfigValue,
} from "../features/strategy/StrategyConfigFields";

vi.mock("../services/strategiesApi", async () => {
  const actual = await vi.importActual<typeof import("../services/strategiesApi")>(
    "../services/strategiesApi",
  );
  return {
    ...actual,
    listStrategies: vi.fn(async () => actual.FALLBACK_STRATEGIES),
  };
});

function Harness() {
  const [value, setValue] = useState<StrategyConfigValue>(defaultStrategyConfig());
  return <StrategyConfigFields value={value} onChange={setValue} />;
}

describe("strategy config fields", () => {
  it("defaults Dual EMA periods to 9 and 21", async () => {
    render(<Harness />);
    await waitFor(() => {
      expect(screen.getByTestId("strategy-id")).toHaveValue("dual_ema");
    });
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(9);
    expect(screen.getByTestId("strategy-param-slowPeriod")).toHaveValue(21);
  });

  it("shows fast < slow cross-field message", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-param-fastPeriod"));
    await user.clear(screen.getByTestId("strategy-param-fastPeriod"));
    await user.type(screen.getByTestId("strategy-param-fastPeriod"), "30");
    expect(screen.getByTestId("strategy-param-error")).toHaveTextContent(
      "Fast period must be less than slow period.",
    );
  });
});
