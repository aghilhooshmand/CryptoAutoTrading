import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";

describe("simulation info tooltips", () => {
  it("opens on keyboard focus and tap without tip icons on obvious fields", async () => {
    const user = userEvent.setup();
    render(<SessionConfigForm onSubmit={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "About Starting capital" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "About Duration" })).not.toBeInTheDocument();

    const allocatedTip = screen.getByRole("button", { name: "About Allocated capital" });
    expect(screen.queryByTestId("tip-allocated-bubble")).not.toBeInTheDocument();

    await act(async () => {
      allocatedTip.focus();
    });
    expect(await screen.findByTestId("tip-allocated-bubble")).toHaveTextContent(
      /allowed to use/i,
    );
    expect(allocatedTip).toHaveAttribute("aria-expanded", "true");

    expect(screen.getByText(/XT Spot VIP0 0\.20%/i)).toBeTruthy();
    expect(screen.getByTestId("sim-fee")).toHaveValue("0.002");
    expect(screen.getByTestId("sim-fee-usdt")).toHaveValue("1");
  });

  it("does not change create payload when tips are used", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SessionConfigForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "About Max trades" }));
    expect(screen.getByTestId("tip-max-trades-bubble")).toBeInTheDocument();
    await user.click(screen.getByTestId("sim-create-start"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      symbol: "btc_usdt",
      maxTrades: 20,
      targetNetProfitRate: "0.01",
    });
  });
});
