import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

vi.mock("../features/market-data/CandleChart", () => ({
  CandleChart: () => <div data-testid="candle-chart-mock">chart</div>,
}));

function mockFetch() {
  return vi.fn(async (input: RequestInfo) => {
    const url = String(input);
    if (url.includes("/settings")) {
      return {
        ok: true,
        json: async () => ({
          symbol: "btc_usdt",
          timeframe: "1h",
          startingCapital: "1000",
          allocatedCapital: "1000",
          maxPositionSize: "1000",
          feeRate: "0.002",
          slippageRate: "0.0005",
          targetNetProfitRate: null,
          maxSessionLossRate: null,
          maxTrades: null,
          strategyId: "dual_ema",
          strategyParams: { fastPeriod: 9, slowPeriod: 21 },
          portfolioMaxLossRate: null,
          portfolioMaxLossAmount: null,
          perSymbolMaxWeight: null,
          preferredAllocationId: null,
          decisionLogMode: "important_only",
          updatedAt: null,
          source: "starters",
          warning: null,
        }),
      };
    }
    if (url.includes("/portfolio")) {
      return {
        ok: true,
        json: async () => ({
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
      };
    }
    if (url.includes("/simulation/sessions/active")) {
      return {
        ok: true,
        json: async () => ({ session: null }),
      };
    }
    if (url.match(/\/simulation\/sessions(\?|$)/)) {
      return {
        ok: true,
        json: async () => ({ sessions: [], totalCount: 0, limit: 50, offset: 0 }),
      };
    }
    if (url.includes("/market/pairs")) {
      return {
        ok: true,
        json: async () => ({
          source: "XT",
          retrievedAt: "2026-08-09T16:00:00.000Z",
          pairs: [],
        }),
      };
    }
    if (url.includes("/strategies") || url.includes("/backtest") || url.includes("/comparisons")) {
      return { ok: true, json: async () => ({ strategies: [], runs: [], comparisons: [] }) };
    }
    return { ok: false, json: async () => ({ error: { code: "error", message: "nope" } }) };
  });
}

describe("simulation responsive smoke", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch());
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
  });

  it("keeps primary Auto Trading controls usable at ~375px", async () => {
    render(
      <MemoryRouter initialEntries={["/auto-trading"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("simulation-badge")).toBeInTheDocument();
    expect(screen.getByTestId("simulation-config-form")).toBeInTheDocument();
    expect(screen.getByTestId("sim-create-start")).toBeInTheDocument();
    expect(screen.getByTestId("simulation-status")).toBeInTheDocument();
    expect(screen.queryByTestId("sim-emergency-stop")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sim-stop")).not.toBeInTheDocument();
    expect(screen.getByTestId("simulation-economics")).toBeInTheDocument();
    expect(screen.getByTestId("decision-journal")).toBeInTheDocument();
    expect(screen.getByTestId("trade-journal")).toBeInTheDocument();
  });
});
