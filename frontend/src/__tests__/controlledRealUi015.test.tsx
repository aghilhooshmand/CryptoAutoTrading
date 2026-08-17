import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import { SimulationHistoryList } from "../features/simulation/SimulationHistoryList";
import type { SimulationSession } from "../services/simulationApi";

function realSessionWithPending(
  overrides: Partial<SimulationSession> = {},
): SimulationSession {
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
    ...overrides,
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
    expect(screen.getByTestId("sim-cash-budget-note").textContent).toMatch(/local budget/i);
  });

  it("shows Real blocked-recovery banner and Resume/Stop at ~375px", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    render(
      <div style={{ width: 375 }}>
        <SessionStatusPanel
          session={realSessionWithPending({
            state: "RECOVERY_BLOCKED",
            pendingConfirmation: null,
            recoveryReason: "real_restart_blocked",
            recoveryDetail: "Real session blocked after restart; never auto-resumed.",
          })}
          onResume={vi.fn()}
          onStop={vi.fn()}
          onEmergencyStop={vi.fn()}
        />
      </div>,
    );
    expect(screen.getByTestId("real-recovery-banner").textContent).toMatch(/never auto-resumes/i);
    expect(screen.getByTestId("sim-resume")).toBeTruthy();
    expect(screen.getByTestId("sim-stop")).toBeTruthy();
    expect(screen.queryByTestId("real-pending-confirm")).toBeNull();
  });
});

describe("Controlled Real create/history labels ~375px", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/settings")) {
          return new Response(
            JSON.stringify({
              symbol: "btc_usdt",
              timeframe: "1h",
              startingCapital: "25",
              allocatedCapital: "25",
              maxPositionSize: "25",
              feeRate: "0.001",
              slippageRate: "0.0005",
              targetNetProfitRate: "0.01",
              maxSessionLossRate: "0.007",
              maxTrades: 20,
              strategyId: "dual_ema",
              strategyParams: { fastPeriod: 9, slowPeriod: 21 },
              decisionLogMode: "important_only",
              source: "saved",
            }),
            { status: 200 },
          );
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
          return new Response(JSON.stringify({ strategies: [] }), { status: 200 });
        }
        if (url.includes("/simulation/sessions")) {
          return new Response(
            JSON.stringify({
              sessions: [
                {
                  id: "11111111-1111-1111-1111-111111111111",
                  mode: "real",
                  label: "REAL",
                  state: "STOPPED",
                  symbol: "btc_usdt",
                  timeframe: "1h",
                  strategyId: "dual_ema",
                  startedAt: "2026-08-16T10:00:00Z",
                  stoppedAt: "2026-08-16T11:00:00Z",
                  stopReason: "manual",
                  createdAt: "2026-08-16T09:59:00Z",
                  finalResultSummary: { complete: true, netPnl: "0", returnPct: "0" },
                },
              ],
              totalCount: 1,
              limit: 50,
              offset: 0,
            }),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("exposes Controlled Real mode selector and budget note", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    const onSubmit = vi.fn();
    render(
      <div style={{ width: 375 }}>
        <SessionConfigForm onSubmit={onSubmit} />
      </div>,
    );
    const mode = await screen.findByTestId("session-mode");
    expect(mode).toHaveValue("simulation");
    await userEvent.selectOptions(mode, "real");
    expect(screen.getByTestId("real-budget-note").textContent).toMatch(/not XT cash/i);
    expect(screen.queryByTestId("sim-allocation")).toBeNull();
  });

  it("labels Real sessions in history", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    render(
      <MemoryRouter>
        <div style={{ width: 375 }}>
          <SimulationHistoryList />
        </div>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("sim-history-label-11111111-1111-1111-1111-111111111111").textContent,
      ).toBe("REAL");
    });
  });
});
