import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutoTradingPage } from "../pages/AutoTradingPage";
import { ComparisonResultsTable } from "../features/comparison/ComparisonResultsTable";
import {
  MAX_COMPARISON_LEGS,
  MIN_COMPARISON_LEGS,
  validateLegCount,
  type StrategyComparison,
} from "../services/comparisonApi";

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
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

describe("comparison API helpers", () => {
  it("accepts 2–5 legs and rejects outside that range", () => {
    expect(validateLegCount(MIN_COMPARISON_LEGS)).toBeNull();
    expect(validateLegCount(MAX_COMPARISON_LEGS)).toBeNull();
    expect(validateLegCount(1)).not.toBeNull();
    expect(validateLegCount(6)).not.toBeNull();
  });
});

describe("comparison UI", () => {
  beforeEach(() => {
    cleanup();
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("hosts Comparison tab with multi-leg form and no winner chrome", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);

    expect(screen.getByRole("tab", { name: /^Comparison$/i })).toBeTruthy();
    await user.click(screen.getByRole("tab", { name: /^Comparison$/i }));

    expect(
      screen.getByRole("heading", { level: 2, name: /Strategy Comparison/i }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run Comparison/i })).toBeTruthy();
    expect(screen.getByTestId("comparison-leg-0")).toBeTruthy();
    expect(screen.getByTestId("comparison-leg-1")).toBeTruthy();
    expect(screen.queryByText(/best strategy/i)).toBeNull();
    expect(screen.queryByLabelText(/winner/i)).toBeNull();
  });

  it("results table shows metrics without winner badge", () => {
    const comparison: StrategyComparison = {
      id: "11111111-1111-1111-1111-111111111111",
      status: "completed",
      symbol: "btc_usdt",
      timeframe: "1h",
      startTime: 1700000000000,
      endTime: 1700100000000,
      startingCapital: "1000",
      allocatedCapital: "1000",
      maxPositionSize: "1000",
      targetNetProfitRate: null,
      maxSessionLossRate: null,
      maxTrades: null,
      feeRate: "0.001",
      slippageRate: "0.0005",
      candleCount: 40,
      buyAndHoldReturnPct: "0.02",
      buyAndHoldNetPnl: "20",
      errorCode: null,
      errorMessage: null,
      createdAt: null,
      completedAt: null,
      legs: [
        {
          ordinal: 0,
          strategyId: "dual_ema",
          strategyParams: { fastPeriod: 9, slowPeriod: 21 },
          backtestRunId: "22222222-2222-2222-2222-222222222222",
          netPnl: "10",
          returnPct: "0.01",
          maxDrawdown: "1",
          maxDrawdownPct: "0.01",
          winRate: "0.5",
          roundTripCount: 2,
          fillCount: 4,
          totalFees: "0.1",
          totalSlippage: "0.05",
          bestTrade: "3",
          worstTrade: "-1",
          buyAndHoldReturnPct: "0.02",
          vsBuyAndHoldReturnPct: "-0.01",
        },
        {
          ordinal: 1,
          strategyId: "rsi",
          strategyParams: { period: 14, overbought: 70, oversold: 30 },
          backtestRunId: "33333333-3333-3333-3333-333333333333",
          netPnl: "5",
          returnPct: "0.005",
          maxDrawdown: "2",
          maxDrawdownPct: "0.02",
          winRate: "0.4",
          roundTripCount: 1,
          fillCount: 2,
          totalFees: "0.05",
          totalSlippage: "0.02",
          bestTrade: "2",
          worstTrade: "-2",
          buyAndHoldReturnPct: "0.02",
          vsBuyAndHoldReturnPct: "-0.015",
        },
      ],
    };
    render(<ComparisonResultsTable comparison={comparison} />);
    expect(screen.getByText(/without an automatic winner/i)).toBeTruthy();
    expect(screen.getByText("dual_ema")).toBeTruthy();
    expect(screen.getByText("rsi")).toBeTruthy();
    expect(screen.queryByText(/best strategy/i)).toBeNull();
    expect(screen.queryByLabelText(/winner/i)).toBeNull();
  });

  it("can add a third leg and cannot go below two", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);
    await user.click(screen.getByRole("tab", { name: /^Comparison$/i }));
    await user.click(screen.getByRole("button", { name: /Add strategy/i }));
    expect(screen.getByTestId("comparison-leg-2")).toBeTruthy();
    const removeButtons = screen.getAllByRole("button", { name: /^Remove$/i });
    expect(removeButtons.length).toBe(3);
  });
});
