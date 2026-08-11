import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestResultsPanel } from "../features/backtest/BacktestResultsPanel";
import type { BacktestRun } from "../services/backtestApi";

describe("backtest results", () => {
  it("shows historical evaluation disclaimer and summary fields", () => {
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
        startingCapital: "1000",
        endingCapital: "1010",
        netPnl: "10",
        returnPct: "0.01",
        tradeCount: 2,
        winRate: "0.5",
        maxDrawdown: "5",
        maxDrawdownPct: "0.005",
        totalFees: "1",
        totalSlippage: "0.5",
        bestTrade: "12",
        worstTrade: "-2",
        buyAndHoldNetPnl: "8",
        buyAndHoldReturnPct: "0.008",
      },
    };
    render(<BacktestResultsPanel run={run} />);
    expect(screen.getByText(/Historical evaluation only/i)).toBeTruthy();
    expect(screen.getByText("10")).toBeTruthy();
  });
});
