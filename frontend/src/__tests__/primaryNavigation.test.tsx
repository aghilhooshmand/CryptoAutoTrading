import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const forbiddenTradingContent = [
  /fear\s*&\s*greed/i,
  /place order/i,
  /real money \(live\)/i,
];

function jsonOk(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200 });
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes("/simulation/sessions/active")) {
        return jsonOk({ session: null });
      }
      if (url.match(/\/simulation\/sessions(\?|$)/) && !url.includes("/active")) {
        return jsonOk({ sessions: [], totalCount: 0, limit: 50, offset: 0 });
      }
      if (url.includes("/settings")) {
        return jsonOk({
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
        });
      }
      if (url.includes("/portfolio")) {
        return jsonOk({
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
        });
      }
      if (url.includes("/strategies")) {
        return jsonOk({
          strategies: [
            {
              id: "dual_ema",
              displayName: "Dual EMA",
              aliases: [],
              parameters: [
                { name: "fastPeriod", type: "int", label: "Fast", default: 9 },
                { name: "slowPeriod", type: "int", label: "Slow", default: 21 },
              ],
              constraints: [],
            },
          ],
        });
      }
      if (url.includes("/market/pairs")) {
        return jsonOk({
          source: "XT",
          retrievedAt: "2026-08-09T16:00:00.000Z",
          pairs: [],
        });
      }
      return new Response(JSON.stringify({ error: { code: "error", message: "nope" } }), {
        status: 404,
      });
    }),
  );
});

describe("primary navigation", () => {
  it("lands on Dashboard from / and exposes three primary areas with labels and icons", async () => {
    const user = userEvent.setup();
    renderAt("/");

    expect(
      await screen.findByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();

    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
    expect(within(dashboardLink).getByText("Dashboard")).toBeInTheDocument();
    expect(dashboardLink.querySelector(".primary-nav-icon")).not.toBeNull();

    await user.click(screen.getByRole("link", { name: "Auto Trading" }));
    expect(
      screen.getByRole("heading", { name: "Auto Trading" }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId("simulation-badge")).toBeInTheDocument();
    expect(screen.getByTestId("simulation-config-form")).toBeInTheDocument();
    const autoTradingLink = screen.getByRole("link", { name: "Auto Trading" });
    expect(
      within(autoTradingLink).getByText("Auto Trading"),
    ).toBeInTheDocument();
    expect(autoTradingLink.querySelector(".primary-nav-icon")).not.toBeNull();
    for (const pattern of forbiddenTradingContent) {
      expect(screen.queryByText(pattern)).not.toBeInTheDocument();
    }

    await user.click(screen.getByRole("link", { name: "Portfolio" }));
    expect(
      screen.getByRole("heading", { name: "Simulation Portfolio" }),
    ).toBeInTheDocument();
    const portfolioLink = screen.getByRole("link", { name: "Portfolio" });
    expect(within(portfolioLink).getByText("Portfolio")).toBeInTheDocument();
    expect(portfolioLink.querySelector(".primary-nav-icon")).not.toBeNull();
    for (const pattern of forbiddenTradingContent) {
      expect(screen.queryByText(pattern)).not.toBeInTheDocument();
    }

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it.each([
    ["/dashboard", "Dashboard"],
    ["/auto-trading", "Auto Trading"],
    ["/portfolio", "Simulation Portfolio"],
  ] as const)("deep-links %s to %s", async (path, title) => {
    renderAt(path);
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
  });
});
