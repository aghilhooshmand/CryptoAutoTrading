import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RealXtAccountPage } from "../pages/RealXtAccountPage";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("RealXtAccountPage", () => {
  it("shows Real XT labeling and credentials-missing error without trading controls", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "credentials_missing",
              message: "XT private credentials are not configured.",
            },
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(
      <MemoryRouter>
        <RealXtAccountPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Real XT Account" })).toBeInTheDocument();
    expect(screen.getByTestId("real-xt-badge")).toHaveTextContent("REAL XT");
    expect(screen.queryByRole("button", { name: /place|cancel|buy|sell/i })).toBeNull();

    await waitFor(() => {
      expect(screen.getByTestId("real-xt-error")).toHaveTextContent("credentials_missing");
    });
  });
});
