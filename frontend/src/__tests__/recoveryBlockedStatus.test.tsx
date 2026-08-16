import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import type { SimulationSession } from "../services/simulationApi";

function baseSession(overrides: Partial<SimulationSession> = {}): SimulationSession {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    mode: "simulation",
    state: "RECOVERY_BLOCKED",
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
    cash: "1000",
    positionSide: "flat",
    positionQty: "0",
    tradeCount: 0,
    strategyFillCount: 0,
    startedAt: "2026-08-16T10:00:00.000Z",
    stoppedAt: null,
    stopReason: null,
    positionFlattenStatus: "n/a",
    lastProcessedCandleOpenTime: 1723802400000,
    recoveryReason: "reconcile_portfolio_mismatch",
    recoveryDetail: "Portfolio cash does not match session",
    lastRecoveryAt: "2026-08-16T12:00:00.000Z",
    skippedGap: null,
    economics: {
      startEquity: "1000",
      cash: "1000",
      markEquity: null,
      markNetPnl: null,
      unrealizedGross: null,
      liquidationEquity: null,
      grossPnl: "0",
      fees: "0",
      slippageCost: "0",
      netPnl: null,
      targetNetProfitRate: "0.01",
      targetNetProfitAmount: "10",
      maxSessionLossRate: "0.01",
      maxSessionLossAmount: "10",
      markPrice: null,
      markSafe: false,
    },
    label: "SIMULATION",
    ...overrides,
  };
}

describe("SessionStatusPanel recovery", () => {
  it("shows RECOVERY_BLOCKED with resume and recovery reason", () => {
    const onResume = vi.fn();
    render(
      <SessionStatusPanel
        session={baseSession()}
        onResume={onResume}
        onStop={vi.fn()}
        onEmergencyStop={vi.fn()}
      />,
    );
    expect(screen.getByTestId("sim-state").textContent).toBe("RECOVERY_BLOCKED");
    expect(screen.getByTestId("sim-recovery-reason").textContent).toBe(
      "reconcile_portfolio_mismatch",
    );
    expect(screen.getByTestId("sim-resume")).toBeTruthy();
    expect(screen.getByTestId("sim-stop")).toBeTruthy();
    expect(screen.getByTestId("sim-emergency-stop")).toBeTruthy();
  });

  it("does not show Resume for normal RUNNING", () => {
    render(
      <SessionStatusPanel
        session={baseSession({ state: "RUNNING", recoveryReason: null, recoveryDetail: null })}
        onResume={vi.fn()}
        onStop={vi.fn()}
        onEmergencyStop={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("sim-resume")).toBeNull();
    expect(screen.getByTestId("sim-stop")).toBeTruthy();
  });
});
