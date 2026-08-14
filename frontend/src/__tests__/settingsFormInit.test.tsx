import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { BacktestConfigForm } from "../features/backtest/BacktestConfigForm";
import { ComparisonConfigForm } from "../features/comparison/ComparisonConfigForm";
import type { OperatorSettings } from "../services/settingsApi";
import { settingsToSharedSeed, comparisonSecondaryLegStarter } from "../features/settings/mapSettingsToForm";

const distinctive: OperatorSettings = {
  symbol: "eth_usdt",
  timeframe: "4h",
  startingCapital: "2500",
  allocatedCapital: "2000",
  maxPositionSize: "500",
  feeRate: "0.001",
  slippageRate: "0.0004",
  targetNetProfitRate: null,
  maxSessionLossRate: null,
  maxTrades: null,
  strategyId: "rsi",
  strategyParams: { period: 14, overbought: 70, oversold: 30 },
  portfolioMaxLossRate: null,
  portfolioMaxLossAmount: null,
  perSymbolMaxWeight: null,
  preferredAllocationId: null,
  updatedAt: "2026-08-12T00:00:00Z",
  source: "saved",
  warning: null,
};

function mockApis(settings: OperatorSettings = distinctive) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/settings")) {
      return new Response(JSON.stringify(settings), { status: 200 });
    }
    if (url.includes("/portfolio")) {
      return new Response(
        JSON.stringify({
          cash: "10000",
          reserved: "0",
          available: "10000",
          deployed: "0",
          equity: "10000",
          equityComplete: true,
          unvaluedAssets: [],
          positions: [],
          holdings: [],
          allocations: [],
          updatedAt: null,
          warning: null,
        }),
        { status: 200 },
      );
    }
    if (url.includes("/strategies")) {
      return new Response(
        JSON.stringify({
          strategies: [
            {
              id: "dual_ema",
              displayName: "Dual EMA",
              aliases: [],
              parameters: [
                { name: "fastPeriod", type: "int", label: "Fast", default: 9 },
                { name: "slowPeriod", type: "int", label: "Slow", default: 21 },
              ],
              constraints: [],
            },
            {
              id: "rsi",
              displayName: "RSI",
              aliases: [],
              parameters: [
                { name: "period", type: "int", label: "Period", default: 14 },
                { name: "overbought", type: "int", label: "Overbought", default: 70 },
                { name: "oversold", type: "int", label: "Oversold", default: 30 },
              ],
              constraints: [],
            },
          ],
        }),
        { status: 200 },
      );
    }
    return new Response(JSON.stringify({}), { status: 404 });
  });
}

describe("mapSettingsToForm", () => {
  it("maps null optional risk to empty strings", () => {
    const seed = settingsToSharedSeed(distinctive);
    expect(seed.targetNetProfitRate).toBe("");
    expect(seed.maxSessionLossRate).toBe("");
    expect(seed.maxTrades).toBe("");
    expect(seed.strategy.strategyId).toBe("rsi");
  });

  it("secondary comparison leg is not forced to preferred strategy", () => {
    expect(comparisonSecondaryLegStarter().strategyId).toBe("rsi");
  });
});

describe("create form init from Settings", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockApis());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("seeds Simulation from Settings with empty optional risk", async () => {
    render(<SessionConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("eth_usdt")).toBeInTheDocument();
    });
    expect(screen.getByTestId("sim-starting")).toHaveValue("2500");
    expect(screen.getByTestId("sim-profit-rate")).toHaveValue("");
    expect(screen.getByTestId("sim-loss-rate")).toHaveValue("");
  });

  it("does not overwrite Simulation draft after Settings load", async () => {
    const user = userEvent.setup();
    render(<SessionConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => expect(screen.getByDisplayValue("eth_usdt")).toBeInTheDocument());
    await user.clear(screen.getByTestId("sim-starting"));
    await user.type(screen.getByTestId("sim-starting"), "111");
    // Re-render same instance is not a remount; assert local edit sticks
    expect(screen.getByTestId("sim-starting")).toHaveValue("111");
  });

  it("seeds Backtest shared fields from Settings", async () => {
    render(<BacktestConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("eth_usdt")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("2500")).toBeInTheDocument();
  });

  it("Backtest Rule change back to preferred restores Settings params", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      mockApis({
        ...distinctive,
        strategyId: "dual_ema",
        strategyParams: { fastPeriod: 10, slowPeriod: 21 },
      }),
    );
    render(<BacktestConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByTestId("strategy-id")).toHaveValue("dual_ema");
    });
    await waitFor(() => {
      expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);
    });

    await user.selectOptions(screen.getByTestId("strategy-id"), "rsi");
    expect(screen.getByTestId("strategy-param-period")).toHaveValue(14);

    await user.selectOptions(screen.getByTestId("strategy-id"), "dual_ema");
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);
  });

  it("seeds Comparison shared fields and first leg only from Settings", async () => {
    // Preferred dual_ema so leg 0 ≠ secondary RSI starter.
    vi.stubGlobal(
      "fetch",
      mockApis({
        ...distinctive,
        strategyId: "dual_ema",
        strategyParams: { fastPeriod: 9, slowPeriod: 21 },
      }),
    );
    render(<ComparisonConfigForm onSubmit={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("eth_usdt")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("2500")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("comparison-leg-0")).toBeInTheDocument();
    });
    const leg0 = screen.getByTestId("comparison-leg-0");
    const leg1 = screen.getByTestId("comparison-leg-1");
    expect(within(leg0).getByTestId("strategy-id")).toHaveValue("dual_ema");
    expect(within(leg1).getByTestId("strategy-id")).toHaveValue("rsi");
  });
});
