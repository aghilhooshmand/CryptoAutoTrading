import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("not found recovery", () => {
  it("shows Not Found for unknown paths and keeps primary navigation", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/this-is-not-a-page"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Not Found" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/not silently redirected/i),
    ).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Auto Trading" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Portfolio" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });
});
