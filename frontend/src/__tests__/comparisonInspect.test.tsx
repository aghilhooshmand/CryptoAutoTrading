import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BacktestRunList } from "../features/backtest/BacktestRunList";
import type { BacktestRun } from "../services/backtestApi";
import { ComparisonResultsTable } from "../features/comparison/ComparisonResultsTable";
import type { StrategyComparison } from "../services/comparisonApi";

const manualRun: BacktestRun = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
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
  targetNetProfitAmount: null,
  maxSessionLossAmount: null,
  maxTrades: null,
  feeRate: "0.001",
  slippageRate: "0.0005",
  strategyId: "dual_ema",
  origin: "manual",
  comparisonId: null,
  candleCount: 40,
  createdAt: null,
  startedAt: null,
  completedAt: null,
  errorCode: null,
  errorMessage: null,
  summary: { returnPct: "0.01", maxDrawdownPct: "0.02" },
};

const comparisonRun: BacktestRun = {
  ...manualRun,
  id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  origin: "comparison",
  comparisonId: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  strategyId: "rsi",
};

describe("comparison inspect / history filter", () => {
  beforeEach(() => {
    cleanup();
  });
  afterEach(() => {
    cleanup();
  });

  it("marks comparison-originated runs when included in history", () => {
    render(
      <BacktestRunList
        runs={[manualRun, comparisonRun]}
        includeComparisonOrigin
        onIncludeComparisonOriginChange={() => undefined}
        onSelect={() => undefined}
        onDelete={() => undefined}
      />,
    );
    expect(screen.getByText(/Include comparison-originated runs/i)).toBeTruthy();
    expect(screen.getByText(/rsi · comparison/i)).toBeTruthy();
  });

  it("offers inspect link from comparison results to backtest run", async () => {
    const user = userEvent.setup();
    let inspected: string | null = null;
    const comparison: StrategyComparison = {
      id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
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
          strategyParams: {},
          backtestRunId: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          netPnl: "1",
          returnPct: "0.001",
          roundTripCount: 0,
          fillCount: 0,
        },
      ],
    };
    render(
      <ComparisonResultsTable
        comparison={comparison}
        onInspectLeg={(id) => {
          inspected = id;
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Open backtest/i }));
    expect(inspected).toBe("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
  });
});
