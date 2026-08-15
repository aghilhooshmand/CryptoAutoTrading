import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutoTradingPage } from "../pages/AutoTradingPage";

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/settings")) {
      return new Response(
        JSON.stringify({
          symbol: "btc_usdt",
          timeframe: "1h",
          startingCapital: "1000",
          allocatedCapital: "1000",
          maxPositionSize: "1000",
          feeRate: "0.002",
          slippageRate: "0.0005",
          targetNetProfitRate: null,
          maxSessionLossRate: null,
          maxTrades: null,
          strategyId: "dual_ema",
          strategyParams: { fastPeriod: 9, slowPeriod: 21 },
          updatedAt: null,
          source: "starters",
          warning: null,
        }),
        { status: 200 },
      );
    }
    if (url.includes("/strategies")) {
      return new Response(JSON.stringify({ strategies: [] }), { status: 200 });
    }
    if (url.includes("/comparisons")) {
      return new Response(JSON.stringify({ comparisons: [] }), { status: 200 });
    }
    if (url.includes("/backtest/runs")) {
      return new Response(JSON.stringify({ runs: [] }), { status: 200 });
    }
    if (url.includes("/simulation")) {
      return new Response(JSON.stringify({ session: null }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 404 });
  });
}

describe("Auto Trading hosts simulation and backtest", () => {
  beforeEach(() => {
    cleanup();
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("uses internal tabs with distinct Simulation and Backtest workflows", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);

    expect(screen.getByRole("tab", { name: /^Simulation$/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /^Backtest$/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /^Comparison$/i })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /^Simulation$/i })).toBeTruthy();

    await user.click(screen.getByRole("tab", { name: /^Backtest$/i }));

    expect(screen.getByRole("heading", { level: 2, name: /^Backtest$/i })).toBeTruthy();
    expect(
      screen.getByText(/Test your strategy using historical market data/i),
    ).toBeTruthy();
    expect(screen.getAllByText(/No real orders are placed/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Run Backtest/i })).toBeTruthy();
    expect(screen.getByText(/Advanced settings/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Recent Backtests/i })).toBeTruthy();
  });
});
