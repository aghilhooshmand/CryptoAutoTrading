import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { SimulationHistoryList } from "../features/simulation/SimulationHistoryList";

const SID = "11111111-1111-1111-1111-111111111111";

describe("simulation history delete", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? "GET").toUpperCase();
        if (method === "DELETE" && url.includes(`/simulation/sessions/${SID}`)) {
          return new Response(null, { status: 204 });
        }
        if (url.includes("/simulation/sessions")) {
          return new Response(
            JSON.stringify({
              sessions: [
                {
                  id: SID,
                  state: "STOPPED",
                  symbol: "btc_usdt",
                  timeframe: "1h",
                  strategyId: "dual_ema",
                  startedAt: "2026-08-15T11:00:00Z",
                  stoppedAt: "2026-08-15T11:30:00Z",
                  stopReason: "manual",
                  createdAt: "2026-08-15T10:59:00Z",
                  finalResultSummary: { complete: true, netPnl: "5", returnPct: "0.01" },
                },
              ],
              totalCount: 1,
              limit: 50,
              offset: 0,
            }),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify({}), { status: 404 });
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("requires confirm before delete and refreshes list", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    let listCalls = 0;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      if (url.includes("/simulation/sessions")) {
        listCalls += 1;
        const sessions =
          listCalls === 1
            ? [
                {
                  id: SID,
                  state: "STOPPED",
                  symbol: "btc_usdt",
                  timeframe: "1h",
                  strategyId: "dual_ema",
                  startedAt: "2026-08-15T11:00:00Z",
                  stoppedAt: "2026-08-15T11:30:00Z",
                  stopReason: "manual",
                  createdAt: "2026-08-15T10:59:00Z",
                  finalResultSummary: { complete: true, netPnl: "5", returnPct: "0.01" },
                },
              ]
            : [];
        return new Response(
          JSON.stringify({ sessions, totalCount: sessions.length, limit: 50, offset: 0 }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({}), { status: 404 });
    });

    render(
      <MemoryRouter>
        <SimulationHistoryList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId(`sim-history-delete-${SID}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`sim-history-delete-${SID}`));
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText(/No saved Simulations yet/i)).toBeInTheDocument();
    });
    confirmSpy.mockRestore();
  });

  it("shows reject message when delete fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "DELETE") {
        return new Response(
          JSON.stringify({
            detail: { error: { code: "session_active", message: "Cannot delete active session" } },
          }),
          { status: 409 },
        );
      }
      if (url.includes("/simulation/sessions")) {
        return new Response(
          JSON.stringify({
            sessions: [
              {
                id: SID,
                state: "STOPPED",
                symbol: "btc_usdt",
                timeframe: "1h",
                strategyId: "dual_ema",
                startedAt: null,
                stoppedAt: null,
                stopReason: null,
                createdAt: "2026-08-15T10:59:00Z",
                finalResultSummary: null,
              },
            ],
            totalCount: 1,
            limit: 50,
            offset: 0,
          }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({}), { status: 404 });
    });

    render(
      <MemoryRouter>
        <SimulationHistoryList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId(`sim-history-delete-${SID}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`sim-history-delete-${SID}`));
    await waitFor(() => {
      expect(screen.getByTestId("sim-history-error")).toHaveTextContent("Cannot delete active session");
    });
  });
});
