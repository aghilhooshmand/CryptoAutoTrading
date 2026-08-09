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

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes("/simulation/sessions/active")) {
        return { ok: true, json: async () => ({ session: null }) };
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
      return {
        ok: false,
        json: async () => ({ error: { code: "error", message: "nope" } }),
      };
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
      screen.getByRole("heading", { name: "Portfolio" }),
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
    ["/portfolio", "Portfolio"],
  ] as const)("deep-links %s to %s", async (path, title) => {
    renderAt(path);
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
  });
});
