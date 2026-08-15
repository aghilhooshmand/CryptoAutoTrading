import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { SimulationHistoryList } from "../features/simulation/SimulationHistoryList";
import { SimulationSessionDetailPage } from "../features/simulation/SimulationSessionDetailPage";

const SID = "11111111-1111-1111-1111-111111111111";

describe("simulation history responsive", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/decisions") || url.includes("/trades")) {
          return new Response(JSON.stringify({ items: [] }), { status: 200 });
        }
        if (url.includes(`/simulation/sessions/${SID}`)) {
          return new Response(
            JSON.stringify({
              id: SID,
              mode: "simulation",
              state: "STOPPED",
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
              decisionLogMode: "full_audit",
              cash: "500",
              positionSide: "flat",
              positionQty: "0",
              tradeCount: 0,
              strategyFillCount: 0,
              startedAt: "2026-08-15T11:00:00Z",
              stoppedAt: "2026-08-15T11:30:00Z",
              stopReason: "manual",
              positionFlattenStatus: "flat",
              lastProcessedCandleOpenTime: null,
              economics: {
                startEquity: "500",
                cash: "500",
                markEquity: null,
                markNetPnl: null,
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
                markPrice: null,
                markSafe: false,
              },
              finalResult: {
                complete: true,
                frozenAt: "2026-08-15T11:30:00Z",
                source: "stop",
                startingCapital: "500",
                endingEquity: "500",
                netPnl: "0",
                returnPct: "0",
                cash: "500",
                fees: "0",
                slippageCost: "0",
                tradeCount: 0,
                strategyFillCount: 0,
                positionFlattenStatus: "flat",
                stopReason: "manual",
                markEquity: null,
                markPrice: null,
              },
              label: "SIMULATION",
            }),
            { status: 200 },
          );
        }
        if (url.includes("/simulation/sessions")) {
          return new Response(
            JSON.stringify({
              sessions: [
                {
                  id: SID,
                  state: "STOPPED",
                  symbol: "btc_usdt",
                  timeframe: "1h",
                  strategyId: "dual_ema",
                  startedAt: "2026-08-15T11:00:00Z",
                  stoppedAt: "2026-08-15T11:30:00Z",
                  stopReason: "manual",
                  createdAt: "2026-08-15T10:59:00Z",
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
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps primary history actions reachable at narrow width", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    render(
      <MemoryRouter>
        <div style={{ width: 375 }}>
          <SimulationHistoryList />
        </div>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId(`sim-history-delete-${SID}`)).toBeInTheDocument());
    expect(screen.getByTestId(`sim-history-open-${SID}`)).toBeVisible();
    expect(screen.getByTestId(`sim-history-delete-${SID}`)).toBeVisible();

    render(
      <MemoryRouter initialEntries={[`/auto-trading/simulation/${SID}`]}>
        <div style={{ width: 375 }}>
          <Routes>
            <Route path="/auto-trading/simulation/:sessionId" element={<SimulationSessionDetailPage />} />
          </Routes>
        </div>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("sim-detail-delete")).toBeInTheDocument());
    expect(screen.getByTestId("sim-detail-delete")).toBeVisible();
    expect(screen.getByTestId("sim-final-result")).toBeVisible();
  });
});
