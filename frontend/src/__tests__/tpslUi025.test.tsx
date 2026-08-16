import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import type { SimulationSession } from "../services/simulationApi";

vi.mock("../services/settingsApi", () => ({
  getSettings: vi.fn(async () => ({
    symbol: "btc_usdt",
    timeframe: "1h",
    startingCapital: "1000",
    allocatedCapital: "1000",
    maxPositionSize: "1000",
    feeRate: "0.001",
    slippageRate: "0.0005",
    targetNetProfitRate: "0.01",
    maxSessionLossRate: "0.01",
    maxTrades: 5,
    strategyId: "dual_ema",
    strategyParams: { fastPeriod: 9, slowPeriod: 21 },
    portfolioMaxLossRate: null,
    portfolioMaxLossAmount: null,
    perSymbolMaxWeight: null,
    preferredAllocationId: null,
    decisionLogMode: "important_only",
    takeProfitPercent: "0.02",
    stopLossPercent: "0.01",
    updatedAt: null,
    source: "starters",
    warning: null,
  })),
}));

vi.mock("../services/portfolioApi", () => ({
  getPortfolio: vi.fn(async () => ({
    funding: "100000",
    available: "100000",
    allocations: [],
  })),
}));

vi.mock("../services/strategiesApi", async () => {
  const actual = await vi.importActual<typeof import("../services/strategiesApi")>(
    "../services/strategiesApi",
  );
  return {
    ...actual,
    listStrategies: vi.fn(async () => actual.FALLBACK_STRATEGIES),
  };
});

function baseSession(overrides: Partial<SimulationSession> = {}): SimulationSession {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    mode: "simulation",
    state: "RUNNING",
    symbol: "btc_usdt",
    timeframe: "1h",
    strategyId: "dual_ema",
    startingCapital: "1000",
    allocatedCapital: "1000",
    maxPositionSize: "500",
    targetNetProfitRate: "0.01",
    maxSessionLossRate: "0.01",
    targetNetProfitAmount: "10",
    maxSessionLossAmount: "10",
    maxTrades: 5,
    durationSeconds: 3600,
    feeRate: "0.001",
    slippageRate: "0.0005",
    decisionLogMode: "important_only",
    takeProfitPercent: "0.02",
    stopLossPercent: "0.01",
    entryFillPrice: "100",
    takeProfitPrice: "102",
    stopLossPrice: "99",
    cash: "900",
    positionSide: "long",
    positionQty: "1",
    tradeCount: 1,
    strategyFillCount: 1,
    startedAt: "2026-08-16T10:00:00.000Z",
    stoppedAt: null,
    stopReason: null,
    positionFlattenStatus: "n/a",
    lastProcessedCandleOpenTime: 1723802400000,
    economics: {
      startEquity: "1000",
      cash: "900",
      markEquity: "1000",
      markNetPnl: "0",
      unrealizedGross: "0",
      liquidationEquity: null,
      grossPnl: "0",
      fees: "0",
      slippageCost: "0",
      netPnl: "0",
      targetNetProfitRate: "0.01",
      targetNetProfitAmount: "10",
      maxSessionLossRate: "0.01",
      maxSessionLossAmount: "10",
      markPrice: "100",
      markSafe: true,
    },
    label: "SIMULATION",
    ...overrides,
  };
}

describe("Feature 025 TP/SL UI", () => {
  it("shows TP%/SL% inputs on session config", async () => {
    render(<SessionConfigForm onSubmit={vi.fn()} />);
    expect(await screen.findByTestId("sim-take-profit-percent")).toBeTruthy();
    expect(screen.getByTestId("sim-stop-loss-percent")).toBeTruthy();
  });

  it("shows absolute protective levels while long", () => {
    render(
      <SessionStatusPanel
        session={baseSession()}
        onStop={vi.fn()}
        onEmergencyStop={vi.fn()}
      />,
    );
    const levels = screen.getByTestId("sim-protective-levels");
    expect(levels.textContent).toContain("100");
    expect(levels.textContent).toContain("102");
    expect(levels.textContent).toContain("99");
  });

  it("shows stop reason after session stop", () => {
    render(
      <SessionStatusPanel
        session={baseSession({
          state: "STOPPED",
          positionSide: "flat",
          positionQty: "0",
          entryFillPrice: null,
          takeProfitPrice: null,
          stopLossPrice: null,
          stopReason: "take_profit",
        })}
        onStop={vi.fn()}
        onEmergencyStop={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("sim-protective-levels")).toBeNull();
    expect(screen.getByTestId("sim-stop-reason").textContent).toBe("take_profit");
  });

  it("keeps TP/SL status fields present at ~375px", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    render(
      <div style={{ width: 375 }}>
        <SessionStatusPanel
          session={baseSession()}
          onStop={vi.fn()}
          onEmergencyStop={vi.fn()}
        />
      </div>,
    );
    expect(screen.getByTestId("sim-protective-levels")).toBeTruthy();
    expect(screen.getByTestId("sim-stop")).toBeTruthy();
  });
});
