import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FreezeStrategyForm } from "../features/evolution/FreezeStrategyForm";

describe("evolution freeze", () => {
  it("shows duplicate/error from onFreeze", async () => {
    const user = userEvent.setup();
    const onFreeze = vi.fn().mockRejectedValue(new Error("Display name already used"));
    render(<FreezeStrategyForm onFreeze={onFreeze} />);
    await user.type(screen.getByTestId("evolution-freeze-name"), "Dup");
    await user.click(screen.getByTestId("evolution-freeze-btn"));
    expect(await screen.findByTestId("evolution-freeze-error")).toHaveTextContent(/already used/i);
  });
});
