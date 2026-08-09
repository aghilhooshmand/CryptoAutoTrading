import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import {
  deriveAmount,
  validateCapitalNesting,
} from "../services/simulationApi";

describe("simulation config validation", () => {
  it("derives USDT amounts from allocated × rate", () => {
    expect(deriveAmount("500", "0.01")).toBe("5");
    expect(deriveAmount("500", "0.007")).toBe("3.5");
  });

  it("rejects invalid capital nesting", () => {
    expect(validateCapitalNesting("100", "200", "50")).toMatch(/allocated/i);
    expect(validateCapitalNesting("500", "500", "500")).toBeNull();
  });

  it("shows live % and amount hints and blocks bad nesting on submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SessionConfigForm onSubmit={onSubmit} />);

    expect(screen.getByTestId("sim-profit-derived")).toHaveTextContent("1.00%");
    expect(screen.getByTestId("sim-profit-derived")).toHaveTextContent("5");
    expect(screen.getByTestId("sim-loss-derived")).toHaveTextContent("0.70%");
    expect(screen.getByTestId("sim-loss-derived")).toHaveTextContent("3.5");

    await user.clear(screen.getByTestId("sim-allocated"));
    await user.type(screen.getByTestId("sim-allocated"), "600");
    await user.click(screen.getByTestId("sim-create-start"));

    expect(screen.getByTestId("sim-config-error")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("sim-real-money-disabled")).toBeDisabled();
  });
});
