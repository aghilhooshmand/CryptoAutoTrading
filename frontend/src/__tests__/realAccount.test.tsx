import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RealAccountPage } from "../pages/RealAccountPage";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("RealAccountPage", () => {
  it("shows Kraken labeling and credentials-missing error without trading controls", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "credentials_missing",
              message: "Kraken private credentials are not configured.",
            },
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(
      <MemoryRouter>
        <RealAccountPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Real Account" })).toBeInTheDocument();
    expect(screen.getByTestId("real-account-badge")).toHaveTextContent("KRAKEN");
    expect(screen.getByText(/Venue:/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /place|cancel|buy|sell/i })).toBeNull();
    expect(screen.queryByRole("textbox", { name: /api key|secret/i })).toBeNull();

    await waitFor(() => {
      expect(screen.getByTestId("real-account-error")).toHaveTextContent(
        "credentials_missing",
      );
    });
  });
});
