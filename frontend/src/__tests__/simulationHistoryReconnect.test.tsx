import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { useSimulationSession } from "../features/simulation/useSimulationSession";
import { SimulationHistoryList } from "../features/simulation/SimulationHistoryList";

function Probe() {
  useSimulationSession();
  return <div data-testid="probe">ok</div>;
}

describe("simulation history reconnect", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("remount/refresh path does not POST stop", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? "GET").toUpperCase();
        calls.push(`${method} ${url}`);
        if (url.includes("/simulation/sessions/active")) {
          return new Response(
            JSON.stringify({
              session: {
                id: "11111111-1111-1111-1111-111111111111",
                mode: "simulation",
                state: "RUNNING",
                symbol: "btc_usdt",
                timeframe: "1h",
                strategyId: "dual_ema",
                startingCapital: "500",
                allocatedCapital: "500",
                maxPositionSize: "500",
                targetNetProfitRate: "0.01",
                maxSessionLossRate: "0.007",
                targetNetProfitAmount: "5",
                maxSessionLossAmount: "3.5",
                maxTrades: 20,
                durationSeconds: 3600,
                feeRate: "0.002",
                slippageRate: "0.0005",
                decisionLogMode: "important_only",
                cash: "500",
                positionSide: "flat",
                positionQty: "0",
                tradeCount: 0,
                strategyFillCount: 0,
                startedAt: "2026-08-15T11:00:00Z",
                stoppedAt: null,
                stopReason: null,
                positionFlattenStatus: "n/a",
                lastProcessedCandleOpenTime: null,
                economics: {
                  startEquity: "500",
                  cash: "500",
                  markEquity: "500",
                  markNetPnl: "0",
                  unrealizedGross: null,
                  liquidationEquity: "500",
                  grossPnl: "0",
                  fees: "0",
                  slippageCost: "0",
                  netPnl: "0",
                  targetNetProfitRate: "0.01",
                  targetNetProfitAmount: "5",
                  maxSessionLossRate: "0.007",
                  maxSessionLossAmount: "3.5",
                  markPrice: "65000",
                  markSafe: true,
                },
                finalResult: null,
                label: "SIMULATION",
              },
            }),
            { status: 200 },
          );
        }
        if (url.includes("/decisions") || url.includes("/trades")) {
          return new Response(JSON.stringify({ items: [] }), { status: 200 });
        }
        if (url.includes("/simulation/sessions/11111111")) {
          return new Response(
            JSON.stringify({
              id: "11111111-1111-1111-1111-111111111111",
              mode: "simulation",
              state: "RUNNING",
              symbol: "btc_usdt",
              timeframe: "1h",
              strategyId: "dual_ema",
              startingCapital: "500",
              allocatedCapital: "500",
              maxPositionSize: "500",
              targetNetProfitRate: "0.01",
              maxSessionLossRate: "0.007",
              targetNetProfitAmount: "5",
              maxSessionLossAmount: "3.5",
              maxTrades: 20,
              durationSeconds: 3600,
              feeRate: "0.002",
              slippageRate: "0.0005",
              decisionLogMode: "important_only",
              cash: "500",
              positionSide: "flat",
              positionQty: "0",
              tradeCount: 0,
              strategyFillCount: 0,
              startedAt: "2026-08-15T11:00:00Z",
              stoppedAt: null,
              stopReason: null,
              positionFlattenStatus: "n/a",
              lastProcessedCandleOpenTime: null,
              economics: {
                startEquity: "500",
                cash: "500",
                markEquity: "500",
                markNetPnl: "0",
                unrealizedGross: null,
                liquidationEquity: "500",
                grossPnl: "0",
                fees: "0",
                slippageCost: "0",
                netPnl: "0",
                targetNetProfitRate: "0.01",
                targetNetProfitAmount: "5",
                maxSessionLossRate: "0.007",
                maxSessionLossAmount: "3.5",
                markPrice: "65000",
                markSafe: true,
              },
              finalResult: null,
              label: "SIMULATION",
            }),
            { status: 200 },
          );
        }
        if (url.includes("/simulation/sessions")) {
          return new Response(
            JSON.stringify({ sessions: [], totalCount: 0, limit: 50, offset: 0 }),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );

    const { unmount } = render(
      <MemoryRouter>
        <Probe />
        <SimulationHistoryList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("probe")).toBeInTheDocument());
    unmount();
    render(
      <MemoryRouter>
        <Probe />
        <SimulationHistoryList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("probe")).toBeInTheDocument());
    expect(calls.some((c) => c.startsWith("POST") && c.includes("/stop"))).toBe(false);
  });
});
