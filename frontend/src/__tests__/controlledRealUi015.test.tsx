import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import type { SimulationSession } from "../services/simulationApi";

function realSessionWithPending(): SimulationSession {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    mode: "real",
    state: "RUNNING",
    symbol: "btc_usdt",
    timeframe: "1h",
    strategyId: "dual_ema",
    startingCapital: "25",
    allocatedCapital: "25",
    maxPositionSize: "25",
    targetNetProfitRate: "0.01",
    maxSessionLossRate: "0.007",
    targetNetProfitAmount: "0.25",
    maxSessionLossAmount: "0.175",
    maxTrades: 20,
    durationSeconds: 3600,
    feeRate: "0.001",
    slippageRate: "0.0005",
    decisionLogMode: "important_only",
    cash: "25",
    cashIsLocalBudgetOnly: true,
    positionSide: "flat",
    positionQty: "0",
    tradeCount: 0,
    strategyFillCount: 0,
    startedAt: "2026-08-16T10:00:00.000Z",
    stoppedAt: null,
    stopReason: null,
    positionFlattenStatus: "n/a",
    lastProcessedCandleOpenTime: 1723802400000,
    pendingConfirmation: {
      id: "22222222-2222-2222-2222-222222222222",
      symbol: "btc_usdt",
      side: "BUY",
      proposedNotional: "25",
      referencePrice: "65000",
      status: "pending",
      createdAt: "2026-08-16T10:00:00.000Z",
      expiresAt: "2026-08-16T10:05:00.000Z",
    },
    economics: {
      startEquity: "25",
      cash: "25",
      markEquity: "25",
      markNetPnl: "0",
      unrealizedGross: "0",
      liquidationEquity: "25",
      grossPnl: "0",
      fees: "0",
      slippageCost: "0",
      netPnl: "0",
      targetNetProfitRate: "0.01",
      targetNetProfitAmount: "0.25",
      maxSessionLossRate: "0.007",
      maxSessionLossAmount: "0.175",
      markPrice: "65000",
      markSafe: true,
    },
    label: "REAL",
  };
}

describe("Controlled Real pending confirm UI ~375px", () => {
  it("shows REAL badge and confirm/decline actions at ~375px", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    const onConfirm = vi.fn();
    const onDecline = vi.fn();
    render(
      <div style={{ width: 375 }}>
        <SessionStatusPanel
          session={realSessionWithPending()}
          onConfirmEntry={onConfirm}
          onDeclineEntry={onDecline}
        />
      </div>,
    );
    expect(screen.getByTestId("real-badge").textContent).toBe("REAL");
    expect(screen.getByTestId("real-pending-confirm")).toBeTruthy();
    expect(screen.getByTestId("real-pending-notional").textContent).toBe("25 USDT");
    fireEvent.click(screen.getByTestId("real-confirm-entry"));
    fireEvent.click(screen.getByTestId("real-decline-entry"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});
