import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  };
}

describe("candle invalidation on selection / failure", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/market/pairs")) {
          return jsonResponse({
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
              {
                symbol: "eth_usdt",
                displayName: "ETH/USDT",
                baseCurrency: "eth",
                quoteCurrency: "usdt",
                status: "tradable",
              },
            ],
          });
        }
        if (url.includes("/market/quote")) {
          const symbol = new URL(url, "http://local").searchParams.get("symbol");
          return jsonResponse({
            symbol,
            lastPrice: symbol === "eth_usdt" ? "3000.00" : "65000.00",
            changePercent: "1.00",
            source: "XT",
            observedAt: "2026-08-09T16:00:00.000Z",
            retrievedAt: "2026-08-09T16:00:01.000Z",
            status: "fresh",
          });
        }
        if (url.includes("/market/candles")) {
          const symbol = new URL(url, "http://local").searchParams.get("symbol");
          if (symbol === "eth_usdt") {
            return jsonResponse(
              {
                error: {
                  code: "market_data_unavailable",
                  message: "candles failed",
                },
              },
              false,
              502,
            );
          }
          return jsonResponse({
            symbol,
            interval: "1h",
            source: "XT",
            retrievedAt: "2026-08-09T16:00:01.000Z",
            candles: [
              {
                openTime: 1786287600000,
                open: "1",
                high: "2",
                low: "0.5",
                close: "1.5",
              },
            ],
          });
        }
        return jsonResponse(
          { error: { code: "error", message: "unexpected" } },
          false,
          500,
        );
      }),
    );
  });

  it("clears prior OHLC when history fetch fails after switching pair", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );

    const allPairs = await screen.findByTestId("all-pairs-list");
    expect(within(allPairs).getByText("BTC/USDT")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("candle-chart")).not.toHaveAttribute("hidden");
    });

    await user.click(within(allPairs).getByText("BTC/USDT"));
    await user.click(within(allPairs).getByText("ETH/USDT"));

    await waitFor(() => {
      expect(screen.getAllByText(/candles failed/i).length).toBeGreaterThan(0);
    });
    expect(screen.getByTestId("candle-chart")).toHaveAttribute("hidden");
  });
});
