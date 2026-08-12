import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";

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

describe("simulation info tooltips", () => {
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

  it("opens on keyboard focus and tap without tip icons on obvious fields", async () => {
    const user = userEvent.setup();
    render(<SessionConfigForm onSubmit={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId("sim-fee")).toHaveValue("0.002");
    });

    expect(screen.queryByRole("button", { name: "About Starting capital" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "About Duration" })).not.toBeInTheDocument();

    const allocatedTip = screen.getByRole("button", { name: "About Allocated capital" });
    expect(screen.queryByTestId("tip-allocated-bubble")).not.toBeInTheDocument();

    await act(async () => {
      allocatedTip.focus();
    });
    expect(await screen.findByTestId("tip-allocated-bubble")).toHaveTextContent(
      /allowed to use/i,
    );
    expect(allocatedTip).toHaveAttribute("aria-expanded", "true");

    expect(screen.getByText(/XT Spot VIP0 0\.20%/i)).toBeTruthy();
    expect(screen.getByTestId("sim-fee-usdt")).toHaveValue("1");
    void user;
  });

  it("does not change create payload when tips are used", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SessionConfigForm onSubmit={onSubmit} />);

    await waitFor(() => {
      expect(screen.getByTestId("sim-max-trades")).toHaveValue("20");
    });

    await user.click(screen.getByRole("button", { name: "About Max trades" }));
    expect(screen.getByTestId("tip-max-trades-bubble")).toBeInTheDocument();
    await user.click(screen.getByTestId("sim-create-start"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      symbol: "btc_usdt",
      maxTrades: 20,
      targetNetProfitRate: "0.01",
    });
  });
});
