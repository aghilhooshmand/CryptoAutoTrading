import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { SimulationHistoryList } from "../features/simulation/SimulationHistoryList";
import { SimulationSessionDetailPage } from "../features/simulation/SimulationSessionDetailPage";

const SESSION_A = "11111111-1111-1111-1111-111111111111";
const SESSION_B = "22222222-2222-2222-2222-222222222222";

function listPayload(offset = 0) {
  const all = [
    {
      id: SESSION_A,
      state: "STOPPED",
      symbol: "btc_usdt",
      timeframe: "1h",
      strategyId: "dual_ema",
      startedAt: "2026-08-15T11:00:00Z",
      stoppedAt: "2026-08-15T11:30:00Z",
      stopReason: "manual",
      createdAt: "2026-08-15T10:59:00Z",
      finalResultSummary: { complete: true, netPnl: "5", returnPct: "0.01" },
    },
    {
      id: SESSION_B,
      state: "CONFIGURED",
      symbol: "eth_usdt",
      timeframe: "4h",
      strategyId: "rsi",
      startedAt: null,
      stoppedAt: null,
      stopReason: null,
      createdAt: "2026-08-14T10:00:00Z",
      finalResultSummary: null,
    },
  ];
  return {
    sessions: all.slice(offset, offset + 50),
    totalCount: all.length,
    limit: 50,
    offset,
  };
}

function detailSession(id: string) {
  return {
    id,
    mode: "simulation",
    state: "STOPPED",
    symbol: "btc_usdt",
    timeframe: "1h",
    strategyId: "dual_ema",
    strategyParams: { fastPeriod: 9, slowPeriod: 21 },
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
    cash: "505",
    positionSide: "flat",
    positionQty: "0",
    tradeCount: 2,
    strategyFillCount: 2,
    startedAt: "2026-08-15T11:00:00Z",
    stoppedAt: "2026-08-15T11:30:00Z",
    stopReason: "manual",
    positionFlattenStatus: "flat",
    lastProcessedCandleOpenTime: 1,
    economics: {
      startEquity: "500",
      cash: "505",
      markEquity: null,
      markNetPnl: null,
      unrealizedGross: null,
      liquidationEquity: "505",
      grossPnl: "6",
      fees: "1",
      slippageCost: "0.5",
      netPnl: "5",
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
      endingEquity: "505",
      netPnl: "5",
      returnPct: "0.01",
      cash: "505",
      fees: "1",
      slippageCost: "0.5",
      tradeCount: 2,
      strategyFillCount: 2,
      positionFlattenStatus: "flat",
      stopReason: "manual",
      markEquity: null,
      markPrice: null,
    },
    label: "SIMULATION",
  };
}

describe("simulation history list", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/simulation/sessions?") || url.endsWith("/simulation/sessions")) {
          return new Response(JSON.stringify(listPayload()), { status: 200 });
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("lists sessions with pagination count and navigates to detail route", async () => {
    render(
      <MemoryRouter>
        <SimulationHistoryList />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("simulation-history-list")).toBeInTheDocument();
    });
    expect(screen.getByTestId("sim-history-count")).toHaveTextContent("1–2 of 2");
    const link = screen.getByTestId(`sim-history-open-${SESSION_A}`);
    expect(link).toHaveAttribute("href", `/auto-trading/simulation/${SESSION_A}`);
  });
});

describe("simulation history detail", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes(`/simulation/sessions/${SESSION_A}/decisions`)) {
          return new Response(
            JSON.stringify({
              items: [
                {
                  id: "d1",
                  createdAt: "2026-08-15T11:01:00Z",
                  candleOpenTime: 1,
                  signal: "BUY",
                  outcome: "rejected",
                  reasonCode: "insufficient_portfolio_available",
                  reasonMessage: "not enough",
                  fastEma: null,
                  slowEma: null,
                },
              ],
            }),
            { status: 200 },
          );
        }
        if (url.includes(`/simulation/sessions/${SESSION_A}/trades`)) {
          return new Response(JSON.stringify({ items: [] }), { status: 200 });
        }
        if (url.includes(`/simulation/sessions/${SESSION_A}`)) {
          return new Response(JSON.stringify(detailSession(SESSION_A)), { status: 200 });
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows freeze, decisionLogMode, risk reason, and no restart", async () => {
    render(
      <MemoryRouter initialEntries={[`/auto-trading/simulation/${SESSION_A}`]}>
        <Routes>
          <Route path="/auto-trading/simulation/:sessionId" element={<SimulationSessionDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("simulation-detail")).toBeInTheDocument();
    });
    expect(screen.getByTestId("sim-final-result")).toBeInTheDocument();
    expect(screen.getByTestId("sim-final-net")).toHaveTextContent("5");
    expect(screen.getByTestId("sim-detail-decision-log-mode")).toHaveTextContent(
      "Important decisions only",
    );
    expect(screen.getByTestId("decision-journal")).toHaveTextContent(
      "insufficient_portfolio_available",
    );
    expect(screen.getByTestId("sim-detail-no-restart")).toBeInTheDocument();
    expect(screen.queryByTestId("sim-detail-start")).not.toBeInTheDocument();
  });
});
