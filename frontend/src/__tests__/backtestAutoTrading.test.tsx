import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutoTradingPage } from "../pages/AutoTradingPage";

describe("Auto Trading hosts simulation and backtest", () => {
  it("renders distinct section headings", () => {
    render(<AutoTradingPage />);
    expect(screen.getByRole("heading", { level: 2, name: /Live simulation/i })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /Historical backtest/i })).toBeTruthy();
  });
});
