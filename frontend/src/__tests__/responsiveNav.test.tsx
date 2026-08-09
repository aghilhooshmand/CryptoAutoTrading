import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import App from "../App";

describe("responsive primary navigation", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1024,
    });
  });

  it("keeps all three primary nav targets present at phone width", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeVisible();

    for (const label of ["Dashboard", "Auto Trading", "Portfolio"] as const) {
      const link = screen.getByRole("link", { name: label });
      expect(link).toBeVisible();
      expect(link.querySelector(".primary-nav-icon")).not.toBeNull();
      expect(link).toHaveTextContent(label);
    }

    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();
  });
});
