import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestResultsPanel } from "../features/backtest/BacktestResultsPanel";
import type { BacktestRun } from "../services/backtestApi";
import {
  formatMoneyUsd,
  formatRateAsPercent,
} from "../services/backtestApi";

describe("formatRateAsPercent", () => {
  it("converts decimal fractions to percent labels", () => {
    expect(formatRateAsPercent("-0.00222313", { signed: true })).toBe("-0.22%");
    expect(formatRateAsPercent("0.01", { signed: true })).toBe("+1.00%");
    expect(formatRateAsPercent("0.5")).toBe("50.00%");
  });
});

describe("formatMoneyUsd", () => {
  it("formats signed money", () => {
    expect(formatMoneyUsd("-1.11")).toBe("-$1.11");
    expect(formatMoneyUsd("1.19")).toBe("+$1.19");
  });
});

describe("backtest results", () => {
  it("shows the operator-facing metrics layout", () => {
    const run: BacktestRun = {
      id: "11111111-1111-1111-1111-111111111111",
      status: "completed",
      symbol: "btc_usdt",
      timeframe: "1h",
      startTime: 1,
      endTime: 2,
      startingCapital: "1000",
      allocatedCapital: "1000",
      maxPositionSize: "1000",
      targetNetProfitRate: null,
      maxSessionLossRate: null,
      targetNetProfitAmount: null,
      maxSessionLossAmount: null,
      maxTrades: null,
      feeRate: "0.001",
      slippageRate: "0.0005",
      strategyId: "dual_ema_9_21",
      candleCount: 40,
      createdAt: null,
      startedAt: null,
      completedAt: null,
      errorCode: null,
      errorMessage: null,
      summary: {
        startingCapital: "500",
        endingCapital: "498.89",
        netPnl: "-1.11",
        returnPct: "-0.00222313",
        tradeCount: 26,
        strategyFillCount: 26,
        roundTripCount: 13,
        winRate: "0.3846",
        maxDrawdown: "3.01",
        maxDrawdownPct: "0.006",
        totalFees: "0.26",
        totalSlippage: "1.30",
        bestTrade: "1.19",
        worstTrade: "-0.63",
        buyAndHoldNetPnl: "0.70",
        buyAndHoldReturnPct: "0.0014",
      },
    };
    render(<BacktestResultsPanel run={run} />);
    expect(screen.getByText(/Historical evaluation only/i)).toBeTruthy();
    expect(screen.getByText("Return")).toBeTruthy();
    expect(screen.getAllByText("-0.22%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Net Profit/Loss")).toBeTruthy();
    expect(screen.getByText("-$1.11")).toBeTruthy();
    expect(screen.getByText("38.46%")).toBeTruthy();
    expect(screen.getByText("-0.60%")).toBeTruthy();
    expect(screen.getByText("$3.01")).toBeTruthy();
    expect(screen.getByText(/26 fills/)).toBeTruthy();
    expect(screen.getByText(/13 round trips/)).toBeTruthy();
    expect(screen.getByText("Trading Costs")).toBeTruthy();
    expect(screen.getByText("$1.56")).toBeTruthy();
    expect(screen.getByText("+$1.19")).toBeTruthy();
    expect(screen.getByText("-$0.63")).toBeTruthy();
    expect(screen.getByText("Buy & Hold")).toBeTruthy();
    expect(screen.getByText("+0.14%")).toBeTruthy();
    expect(screen.getByText("Difference")).toBeTruthy();
    expect(screen.getByText("-0.36%")).toBeTruthy();
  });
});
