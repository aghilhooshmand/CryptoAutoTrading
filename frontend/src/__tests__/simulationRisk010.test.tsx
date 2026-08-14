/** Feature 010 Simulation risk UI: available check, bind, journal reasons. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { DecisionJournal } from "../features/simulation/DecisionJournal";

const settings = {
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
  portfolioMaxLossRate: "0.05",
  portfolioMaxLossAmount: null,
  perSymbolMaxWeight: "0.3",
  preferredAllocationId: "alloc-1",
  updatedAt: null,
  source: "saved" as const,
  warning: null,
};

const portfolio = {
  cash: "1000",
  reserved: "400",
  available: "600",
  deployed: "0",
  equity: "1000",
  equityComplete: true,
  unvaluedAssets: [],
  positions: [],
  holdings: [],
  allocations: [
    {
      id: "alloc-1",
      label: "Sleeve A",
      reservedSize: "400",
      targetRef: null,
      createdAt: "2026-08-14T00:00:00Z",
      updatedAt: "2026-08-14T00:00:00Z",
    },
  ],
  updatedAt: null,
  warning: null,
};

describe("simulation risk UI (Feature 010)", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/settings")) {
          return new Response(JSON.stringify(settings), { status: 200 });
        }
        if (url.includes("/portfolio")) {
          return new Response(JSON.stringify(portfolio), { status: 200 });
        }
        if (url.includes("/strategies")) {
          return new Response(JSON.stringify({ strategies: [] }), { status: 200 });
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows Portfolio available and blocks allocated above available", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SessionConfigForm onSubmit={onSubmit} />);
    await waitFor(() => {
      expect(screen.getByTestId("sim-portfolio-available")).toHaveTextContent("600");
    });
    await waitFor(() => {
      expect(screen.getByTestId("sim-allocation")).toHaveValue("alloc-1");
    });
    await user.clear(screen.getByTestId("sim-allocated"));
    await user.type(screen.getByTestId("sim-allocated"), "700");
    await user.clear(screen.getByTestId("sim-starting"));
    await user.type(screen.getByTestId("sim-starting"), "700");
    await user.clear(screen.getByTestId("sim-max-position"));
    await user.type(screen.getByTestId("sim-max-position"), "700");
    await user.click(screen.getByTestId("sim-create-start"));
    expect(screen.getByTestId("sim-config-error")).toHaveTextContent(/available/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("prefills portfolio risk defaults from Settings", async () => {
    render(<SessionConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByTestId("sim-portfolio-loss-rate")).toHaveValue("0.05");
    });
    expect(screen.getByTestId("sim-per-symbol-weight")).toHaveValue("0.3");
  });

  it("renders decision reason code and message", () => {
    render(
      <DecisionJournal
        items={[
          {
            id: "1",
            createdAt: "2026-08-14T00:00:00Z",
            candleOpenTime: null,
            signal: "BUY",
            outcome: "rejected",
            reasonCode: "allocation_exposure_exceeded",
            reasonMessage: "Trade would exceed the bound allocation’s reserved size.",
            fastEma: null,
            slowEma: null,
          },
        ]}
      />,
    );
    expect(screen.getByText(/allocation_exposure_exceeded/)).toBeInTheDocument();
    expect(screen.getByText(/reserved size/i)).toBeInTheDocument();
  });
});
