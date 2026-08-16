import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import type { SimulationSession } from "../services/simulationApi";

function blockedSession(): SimulationSession {
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
  };
}

describe("recovery UI ~375px", () => {
  it("keeps RECOVERY_BLOCKED Resume/Stop controls present at ~375px", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    render(
      <div style={{ width: 375 }}>
        <SessionStatusPanel
          session={blockedSession()}
          onResume={vi.fn()}
          onStop={vi.fn()}
          onEmergencyStop={vi.fn()}
        />
      </div>,
    );
    expect(screen.getByTestId("sim-state").textContent).toBe("RECOVERY_BLOCKED");
    expect(screen.getByTestId("sim-resume")).toBeInTheDocument();
    expect(screen.getByTestId("sim-stop")).toBeInTheDocument();
    expect(screen.getByTestId("sim-emergency-stop")).toBeInTheDocument();
    expect(screen.getByTestId("sim-recovery-reason")).toBeInTheDocument();
  });
});
