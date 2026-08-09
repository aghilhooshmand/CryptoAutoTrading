import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

vi.mock("../features/market-data/CandleChart", () => ({
  CandleChart: () => <div data-testid="candle-chart-mock">chart</div>,
}));

function mockMarketFetch() {
  return vi.fn(async (input: RequestInfo) => {
    const url = String(input);
    if (url.includes("/market/pairs")) {
      return {
        ok: true,
        json: async () => ({
          source: "XT",
          retrievedAt: "2026-08-09T16:00:00.000Z",
          pairs: [
            {
              symbol: "btc_usdt",
              displayName: "BTC/USDT",
              baseCurrency: "btc",
              quoteCurrency: "usdt",
              status: "tradable",
            },
          ],
        }),
      };
    }
    if (url.includes("/market/quote")) {
      return {
        ok: true,
        json: async () => ({
          symbol: "btc_usdt",
          lastPrice: "65220.00",
          changePercent: "0.19",
          source: "XT",
          observedAt: "2026-08-09T16:00:00.000Z",
          retrievedAt: "2026-08-09T16:00:01.000Z",
          status: "fresh",
        }),
      };
    }
    if (url.includes("/market/candles")) {
      return {
        ok: true,
        json: async () => ({
          symbol: "btc_usdt",
          interval: "1h",
          source: "XT",
          retrievedAt: "2026-08-09T16:00:01.000Z",
          candles: [],
        }),
      };
    }
    return { ok: false, json: async () => ({ error: { code: "error", message: "nope" } }) };
  });
}

describe("market responsive smoke", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockMarketFetch());
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
  });

  it("keeps pair search and refresh controls present at ~375px", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("dashboard-market")).toBeInTheDocument();
    expect(screen.getByTestId("pair-search")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });
});
