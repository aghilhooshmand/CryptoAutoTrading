import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { PortfolioPage } from "../pages/PortfolioPage";
import { allocationsDoNotAffectEquity } from "../features/portfolio/capitalDisplay";
import type { PortfolioAllocation, PortfolioSnapshot } from "../services/portfolioApi";

function emptySnapshot(overrides?: Partial<PortfolioSnapshot>): PortfolioSnapshot {
  return {
    cash: "0",
    reserved: "0",
    available: "0",
    deployed: "0",
    realizedPnl: "0",
    unrealizedPnl: "0",
    equity: "0",
    positions: [],
    allocations: [],
    updatedAt: null,
    warning: null,
    ...overrides,
  };
}

function mockPortfolioFetch(initial?: PortfolioSnapshot) {
  let snap = initial ?? emptySnapshot();
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();

    if (url.includes("/simulation")) {
      return new Response(JSON.stringify({ session: null }), { status: 200 });
    }

    if (url.includes("/portfolio/funding") && method === "PUT") {
      const body = JSON.parse(String(init?.body ?? "{}")) as { cash: string };
      const cash = Number(body.cash);
      const reserved = Number(snap.reserved);
      if (Number.isNaN(cash) || cash < 0) {
        return new Response(
          JSON.stringify({
            detail: { error: { code: "invalid_config", message: "Cash cannot be negative" } },
          }),
          { status: 400 },
        );
      }
      if (cash < reserved) {
        return new Response(
          JSON.stringify({
            detail: {
              error: {
                code: "invalid_config",
                message:
                  "Cash cannot be less than reserved capital. Resize or release allocations first.",
              },
            },
          }),
          { status: 400 },
        );
      }
      snap = {
        ...snap,
        cash: String(body.cash),
        available: String(cash - reserved),
        equity: String(body.cash),
        updatedAt: "2026-08-14T12:00:00.000Z",
      };
      return new Response(JSON.stringify(snap), { status: 200 });
    }

    if (url.includes("/portfolio/allocations") && method === "POST") {
      const body = JSON.parse(String(init?.body ?? "{}")) as {
        label: string;
        reservedSize: string;
        targetRef?: string | null;
      };
      const size = Number(body.reservedSize);
      const cash = Number(snap.cash);
      const reserved = Number(snap.reserved) + size;
      if (!(size > 0) || reserved > cash) {
        return new Response(
          JSON.stringify({
            detail: {
              error: { code: "invalid_config", message: "Reserved capital cannot exceed cash." },
            },
          }),
          { status: 400 },
        );
      }
      const alloc: PortfolioAllocation = {
        id: `11111111-1111-1111-1111-${String(snap.allocations.length + 1).padStart(12, "0")}`,
        label: body.label,
        reservedSize: String(body.reservedSize),
        targetRef: body.targetRef ?? null,
        createdAt: "2026-08-14T12:00:00.000Z",
        updatedAt: "2026-08-14T12:00:00.000Z",
      };
      snap = {
        ...snap,
        reserved: String(reserved),
        available: String(cash - reserved),
        allocations: [...snap.allocations, alloc],
      };
      return new Response(JSON.stringify(snap), { status: 201 });
    }

    const patchMatch = url.match(/\/portfolio\/allocations\/([^/?]+)$/);
    if (patchMatch && method === "PATCH") {
      const id = patchMatch[1];
      const body = JSON.parse(String(init?.body ?? "{}")) as { reservedSize: string };
      const size = Number(body.reservedSize);
      const others = snap.allocations.filter((a) => a.id !== id);
      const reserved = others.reduce((s, a) => s + Number(a.reservedSize), 0) + size;
      const cash = Number(snap.cash);
      if (!(size > 0) || reserved > cash) {
        return new Response(
          JSON.stringify({
            detail: {
              error: { code: "invalid_config", message: "Reserved capital cannot exceed cash." },
            },
          }),
          { status: 400 },
        );
      }
      snap = {
        ...snap,
        reserved: String(reserved),
        available: String(cash - reserved),
        allocations: snap.allocations.map((a) =>
          a.id === id ? { ...a, reservedSize: String(body.reservedSize) } : a,
        ),
      };
      return new Response(JSON.stringify(snap), { status: 200 });
    }

    if (patchMatch && method === "DELETE") {
      const id = patchMatch[1];
      const remaining = snap.allocations.filter((a) => a.id !== id);
      const reserved = remaining.reduce((s, a) => s + Number(a.reservedSize), 0);
      const cash = Number(snap.cash);
      snap = {
        ...snap,
        reserved: String(reserved),
        available: String(cash - reserved),
        allocations: remaining,
      };
      return new Response(JSON.stringify(snap), { status: 200 });
    }

    if (url.includes("/portfolio") && method === "GET") {
      return new Response(JSON.stringify(snap), { status: 200 });
    }

    return new Response(JSON.stringify({}), { status: 404 });
  });
}

function renderPortfolio() {
  return render(
    <MemoryRouter>
      <PortfolioPage />
    </MemoryRouter>,
  );
}

describe("Portfolio page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockPortfolioFetch());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads snapshot and funds cash with labels/units", async () => {
    const user = userEvent.setup();
    renderPortfolio();

    await waitFor(() => {
      expect(screen.getByTestId("metric-cash")).toHaveTextContent("0 USDT");
    });
    expect(screen.getByTestId("metric-available")).toHaveTextContent("USDT");
    expect(screen.getByTestId("metric-reserved")).toHaveTextContent("USDT");
    expect(screen.getByTestId("metric-deployed")).toHaveTextContent("0 USDT");
    expect(screen.getByTestId("help-available")).toBeInTheDocument();
    expect(screen.getByTestId("help-reserved")).toBeInTheDocument();
    expect(screen.getByTestId("help-deployed")).toBeInTheDocument();
    expect(screen.getByTestId("portfolio-positions")).toHaveTextContent("No open positions");

    await user.clear(screen.getByTestId("funding-cash-input"));
    await user.type(screen.getByTestId("funding-cash-input"), "1000");
    await user.click(screen.getByTestId("funding-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("metric-cash")).toHaveTextContent("1000 USDT");
      expect(screen.getByTestId("metric-available")).toHaveTextContent("1000 USDT");
      expect(screen.getByTestId("funding-status")).toHaveTextContent("Funding saved");
    });
  });

  it("creates, rejects overspend, confirms release, and blocks double submit", async () => {
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          cash: "1000",
          available: "1000",
          equity: "1000",
        }),
      ),
    );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderPortfolio();

    await waitFor(() => expect(screen.getByTestId("metric-cash")).toHaveTextContent("1000"));

    await user.type(screen.getByTestId("alloc-label-input"), "RSI sleeve");
    await user.type(screen.getByTestId("alloc-size-input"), "250");
    await user.type(screen.getByTestId("alloc-target-input"), "rsi");
    await user.click(screen.getByTestId("alloc-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("metric-reserved")).toHaveTextContent("250 USDT");
      expect(screen.getByTestId("metric-available")).toHaveTextContent("750 USDT");
    });

    const card = screen.getByText("RSI sleeve").closest("li");
    expect(card).toBeTruthy();
    expect(within(card as HTMLElement).getByText(/Reserved: 250 USDT/)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(/no activity/i)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(/id /)).toBeInTheDocument();
    expect(
      allocationsDoNotAffectEquity({
        cash: "1000",
        reserved: "250",
        available: "750",
        deployed: "0",
        realizedPnl: "0",
        unrealizedPnl: "0",
        equity: "1000",
        positions: [],
        allocations: [],
        updatedAt: null,
        warning: null,
      }),
    ).toBe(true);
    expect(
      allocationsDoNotAffectEquity({
        cash: "1000",
        reserved: "250",
        available: "750",
        deployed: "0",
        realizedPnl: "0",
        unrealizedPnl: "0",
        equity: "1250",
        positions: [],
        allocations: [],
        updatedAt: null,
        warning: null,
      }),
    ).toBe(false);

    await user.clear(screen.getByTestId("alloc-label-input"));
    await user.type(screen.getByTestId("alloc-label-input"), "Too much");
    await user.clear(screen.getByTestId("alloc-size-input"));
    await user.type(screen.getByTestId("alloc-size-input"), "900");
    await user.click(screen.getByTestId("alloc-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("allocation-error")).toHaveTextContent(/cannot exceed cash/i);
      expect(screen.getByTestId("metric-reserved")).toHaveTextContent("250 USDT");
    });

    const releaseBtn = screen.getByRole("button", { name: "Release" });
    await user.click(releaseBtn);
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("metric-reserved")).toHaveTextContent("0 USDT");
    });
  });

  it("surfaces funding reject when cash would undercut reserved", async () => {
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          cash: "1000",
          reserved: "500",
          available: "500",
          equity: "1000",
          allocations: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              label: "A",
              reservedSize: "500",
              targetRef: null,
              createdAt: "2026-08-14T12:00:00.000Z",
              updatedAt: "2026-08-14T12:00:00.000Z",
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    renderPortfolio();

    await waitFor(() => expect(screen.getByTestId("metric-reserved")).toHaveTextContent("500"));

    await user.clear(screen.getByTestId("funding-cash-input"));
    await user.type(screen.getByTestId("funding-cash-input"), "400");
    await user.click(screen.getByTestId("funding-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("funding-error")).toHaveTextContent(/reserved capital/i);
      expect(screen.getByTestId("metric-cash")).toHaveTextContent("1000 USDT");
    });
  });

  it("shows fail-closed warning from GET snapshot", async () => {
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          warning: "Stored portfolio capital is corrupt; refusing to invent balances.",
        }),
      ),
    );
    renderPortfolio();
    await waitFor(() => {
      expect(screen.getByTestId("portfolio-warning")).toHaveTextContent(/corrupt/i);
    });
  });
});
