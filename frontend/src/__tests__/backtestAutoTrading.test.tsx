import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutoTradingPage } from "../pages/AutoTradingPage";

describe("Auto Trading hosts simulation and backtest", () => {
  it("uses internal tabs with distinct Simulation and Backtest workflows", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);

    expect(screen.getByRole("tab", { name: /^Simulation$/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /^Backtest$/i })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /^Simulation$/i })).toBeTruthy();

    await user.click(screen.getByRole("tab", { name: /^Backtest$/i }));

    expect(screen.getByRole("heading", { level: 2, name: /^Backtest$/i })).toBeTruthy();
    expect(
      screen.getByText(/Test your strategy using historical market data/i),
    ).toBeTruthy();
    expect(screen.getByText(/No real orders are placed/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run Backtest/i })).toBeTruthy();
    expect(screen.getByText(/Advanced settings/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Recent Backtests/i })).toBeTruthy();
  });
});
