import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "../App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const forbiddenContent = [
  /\$[0-9]/i,
  /fear\s*&\s*greed/i,
  /open position/i,
  /unrealized/i,
  /BTC\/USDT/i,
  /place order/i,
];

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
    expect(screen.getByText(/foundation placeholder/i)).toBeInTheDocument();
    const autoTradingLink = screen.getByRole("link", { name: "Auto Trading" });
    expect(
      within(autoTradingLink).getByText("Auto Trading"),
    ).toBeInTheDocument();
    expect(autoTradingLink.querySelector(".primary-nav-icon")).not.toBeNull();

    await user.click(screen.getByRole("link", { name: "Portfolio" }));
    expect(
      screen.getByRole("heading", { name: "Portfolio" }),
    ).toBeInTheDocument();
    const portfolioLink = screen.getByRole("link", { name: "Portfolio" });
    expect(within(portfolioLink).getByText("Portfolio")).toBeInTheDocument();
    expect(portfolioLink.querySelector(".primary-nav-icon")).not.toBeNull();

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();

    for (const pattern of forbiddenContent) {
      expect(screen.queryByText(pattern)).not.toBeInTheDocument();
    }
  });

  it.each([
    ["/dashboard", "Dashboard"],
    ["/auto-trading", "Auto Trading"],
    ["/portfolio", "Portfolio"],
  ] as const)("deep-links %s to %s", (path, title) => {
    renderAt(path);
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
  });
});
