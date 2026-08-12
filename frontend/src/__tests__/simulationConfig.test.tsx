import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import {
  deriveAmount,
  validateCapitalNesting,
} from "../services/simulationApi";

const seededSettings = {
  symbol: "btc_usdt",
  timeframe: "1h",
  startingCapital: "500",
  allocatedCapital: "500",
  maxPositionSize: "500",
  feeRate: "0.002",
  slippageRate: "0.0005",
  targetNetProfitRate: "0.01",
  maxSessionLossRate: "0.007",
  maxTrades: 20,
  strategyId: "dual_ema",
  strategyParams: { fastPeriod: 9, slowPeriod: 21 },
  updatedAt: null,
  source: "saved" as const,
  warning: null,
};

describe("simulation config validation", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/settings")) {
          return new Response(JSON.stringify(seededSettings), { status: 200 });
        }
        if (url.includes("/strategies")) {
          return new Response(JSON.stringify({ strategies: [] }), { status: 200 });
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("derives USDT amounts from allocated × rate", () => {
    expect(deriveAmount("500", "0.01")).toBe("5");
    expect(deriveAmount("500", "0.007")).toBe("3.5");
  });

  it("rejects invalid capital nesting", () => {
    expect(validateCapitalNesting("100", "200", "50")).toMatch(/allocated/i);
    expect(validateCapitalNesting("500", "500", "500")).toBeNull();
  });

  it("shows live % and amount hints and blocks bad nesting on submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SessionConfigForm onSubmit={onSubmit} />);

    await waitFor(() => {
      expect(screen.getByTestId("sim-profit-derived")).toHaveTextContent("1.00%");
    });
    expect(screen.getByTestId("sim-profit-derived")).toHaveTextContent("5");
    expect(screen.getByTestId("sim-loss-derived")).toHaveTextContent("0.70%");
    expect(screen.getByTestId("sim-loss-derived")).toHaveTextContent("3.5");

    await user.clear(screen.getByTestId("sim-allocated"));
    await user.type(screen.getByTestId("sim-allocated"), "600");
    await user.click(screen.getByTestId("sim-create-start"));

    expect(screen.getByTestId("sim-config-error")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("sim-real-money-disabled")).toBeDisabled();
  });
});
