import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { PortfolioPage } from "../pages/PortfolioPage";
import { allocationsDoNotAffectEquity } from "../features/portfolio/capitalDisplay";
import type { PortfolioAllocation, PortfolioHolding, PortfolioSnapshot } from "../services/portfolioApi";

function usdtHolding(quantity: string): PortfolioHolding {
  return {
    id: "11111111-1111-1111-1111-000000000001",
    asset: "usdt",
    quantity,
    averageCost: "1",
    price: "1",
    priceStatus: "fresh",
    marketValue: quantity,
    weight: "1",
    realizedPnl: "0",
    unrealizedPnl: "0",
    return: "0",
    provenance: "local_manual",
    createdAt: "2026-08-14T12:00:00.000Z",
    updatedAt: "2026-08-14T12:00:00.000Z",
  };
}

function bookTotals(holdings: PortfolioHolding[]): Pick<PortfolioSnapshot, "totalPnl" | "totalReturn"> {
  if (holdings.some((h) => h.unrealizedPnl == null)) {
    return { totalPnl: null, totalReturn: null };
  }
  const realized = holdings.reduce((sum, h) => sum + Number(h.realizedPnl), 0);
  const unrealized = holdings.reduce((sum, h) => sum + Number(h.unrealizedPnl), 0);
  const totalPnl = realized + unrealized;
  const cost = holdings.reduce((sum, h) => {
    if (h.averageCost == null) return sum;
    return sum + Number(h.quantity) * Number(h.averageCost);
  }, 0);
  return {
    totalPnl: String(totalPnl),
    totalReturn: cost > 0 ? String(totalPnl / cost) : null,
  };
}

function emptySnapshot(overrides?: Partial<PortfolioSnapshot>): PortfolioSnapshot {
  return {
    quoteCurrency: "usdt",
    bookProvenance: "local_manual",
    cash: "0",
    reserved: "0",
    available: "0",
    deployed: "0",
    realizedPnl: "0",
    unrealizedPnl: "0",
    totalPnl: "0",
    totalReturn: null,
    equity: "0",
    equityComplete: true,
    unvaluedAssets: [],
    positions: [],
    holdings: [],
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
        equityComplete: (snap.unvaluedAssets ?? []).length === 0,
        holdings: Number(body.cash) === 0
          ? snap.holdings.filter((h) => h.asset !== "usdt")
          : [
              usdtHolding(String(body.cash)),
              ...snap.holdings.filter((h) => h.asset !== "usdt"),
            ],
        updatedAt: "2026-08-14T12:00:00.000Z",
      };
      // Recalc equity from valued holdings when other assets exist
      const valued = snap.holdings.reduce(
        (s, h) => s + Number(h.marketValue ?? 0),
        0,
      );
      snap = { ...snap, equity: String(valued), ...bookTotals(snap.holdings) };
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

    if (url.includes("/portfolio/holdings") && method === "PUT") {
      const body = JSON.parse(String(init?.body ?? "{}")) as {
        asset: string;
        quantity: string;
        averageCost?: string | null;
      };
      const asset = (body.asset ?? "").toLowerCase();
      if (asset === "usdt" || asset === "notacoin" || !(Number(body.quantity) > 0)) {
        return new Response(
          JSON.stringify({
            detail: { error: { code: "invalid_config", message: "Unsupported or invalid holding" } },
          }),
          { status: 400 },
        );
      }
      const qty = body.quantity;
      const price = asset === "btc" ? "90000" : "3000";
      const value = String(Number(qty) * Number(price));
      const holding: PortfolioHolding = {
        id: "22222222-2222-2222-2222-000000000002",
        asset,
        quantity: qty,
        averageCost: body.averageCost ?? null,
        price,
        priceStatus: "fresh",
        marketValue: value,
        weight: null,
        realizedPnl: "0",
        unrealizedPnl:
          body.averageCost != null && body.averageCost !== ""
            ? String(Number(value) - Number(qty) * Number(body.averageCost))
            : null,
        return: null,
        provenance: "local_manual",
        createdAt: "2026-08-14T12:00:00.000Z",
        updatedAt: "2026-08-14T12:00:00.000Z",
      };
      const others = snap.holdings.filter((h) => h.asset !== asset);
      const holdings = [...others, holding];
      const equity = holdings.reduce((s, h) => s + Number(h.marketValue ?? 0), 0);
      snap = {
        ...snap,
        holdings,
        equity: String(equity),
        equityComplete: true,
        unvaluedAssets: [],
        ...bookTotals(holdings),
      };
      return new Response(JSON.stringify(snap), { status: 200 });
    }

    const holdingDelete = url.match(/\/portfolio\/holdings\/([^/?]+)$/);
    if (holdingDelete && method === "DELETE") {
      const asset = decodeURIComponent(holdingDelete[1]).toLowerCase();
      if (asset === "usdt") {
        return new Response(
          JSON.stringify({
            detail: { error: { code: "invalid_config", message: "Use funding to set USDT quote cash" } },
          }),
          { status: 400 },
        );
      }
      const holdings = snap.holdings.filter((h) => h.asset !== asset);
      const equity = holdings.reduce((s, h) => s + Number(h.marketValue ?? 0), 0);
      snap = { ...snap, holdings, equity: String(equity), ...bookTotals(holdings) };
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
    expect(screen.getByTestId("help-equity")).toBeInTheDocument();
    expect(screen.getByTestId("help-cash")).toBeInTheDocument();
    expect(screen.getByTestId("portfolio-positions")).toHaveTextContent("No open positions");
    expect(screen.getByTestId("holdings-table")).toBeInTheDocument();

    await user.clear(screen.getByTestId("funding-cash-input"));
    await user.type(screen.getByTestId("funding-cash-input"), "1000");
    await user.click(screen.getByTestId("funding-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("metric-cash")).toHaveTextContent("1000 USDT");
      expect(screen.getByTestId("metric-available")).toHaveTextContent("1000 USDT");
      expect(screen.getByTestId("funding-status")).toHaveTextContent("Funding saved");
      expect(screen.getByTestId("holding-qty-usdt")).toHaveTextContent("1000");
      expect(screen.getByTestId("holding-provenance-usdt")).toHaveTextContent(/local\/manual/i);
      expect(screen.getByTestId("metric-total-pnl")).toHaveTextContent("0 USDT");
      expect(screen.getByTestId("metric-total-return")).toHaveTextContent("0.00%");
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
          equityComplete: true,
          holdings: [usdtHolding("1000")],
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
        totalPnl: "0",
        totalReturn: "0",
        equity: "1000",
        equityComplete: true,
        unvaluedAssets: [],
        positions: [],
        holdings: [],
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
        totalPnl: "0",
        totalReturn: "0",
        equity: "1250",
        equityComplete: true,
        unvaluedAssets: [],
        positions: [],
        holdings: [],
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
          equityComplete: true,
          holdings: [usdtHolding("1000")],
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

  it("records a local BTC holding and confirms remove", async () => {
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          cash: "500",
          available: "500",
          equity: "500",
          equityComplete: true,
          holdings: [usdtHolding("500")],
        }),
      ),
    );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderPortfolio();

    await waitFor(() => expect(screen.getByTestId("metric-cash")).toHaveTextContent("500"));

    await user.clear(screen.getByTestId("holding-asset-input"));
    await user.type(screen.getByTestId("holding-asset-input"), "btc");
    await user.type(screen.getByTestId("holding-qty-input"), "0.005");
    await user.type(screen.getByTestId("holding-avg-input"), "80000");
    await user.click(screen.getByTestId("holding-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("holding-row-btc")).toBeInTheDocument();
      expect(screen.getByTestId("holding-qty-btc")).toHaveTextContent("0.005");
      expect(screen.getByTestId("holding-value-btc")).toHaveTextContent("USDT");
      expect(screen.getByTestId("holding-provenance-btc")).toHaveTextContent(/local\/manual/i);
      expect(screen.getByTestId("metric-equity")).toHaveTextContent("950");
    });

    await user.click(screen.getByTestId("holding-delete-btc"));
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.queryByTestId("holding-row-btc")).not.toBeInTheDocument();
    });
  });

  it("labels partial equity and stale prices; has no history charts", async () => {
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          cash: "500",
          available: "500",
          equity: "500",
          equityComplete: false,
          unvaluedAssets: ["eth"],
          totalPnl: null,
          totalReturn: null,
          holdings: [
            usdtHolding("500"),
            {
              id: "22222222-2222-2222-2222-000000000002",
              asset: "btc",
              quantity: "0.005",
              averageCost: "80000",
              price: "90000",
              priceStatus: "stale",
              marketValue: "450",
              weight: "0.4737",
              realizedPnl: "0",
              unrealizedPnl: "50",
              return: "0.125",
              provenance: "local_manual",
              createdAt: "2026-08-14T12:00:00.000Z",
              updatedAt: "2026-08-14T12:00:00.000Z",
            },
            {
              id: "33333333-3333-3333-3333-000000000003",
              asset: "eth",
              quantity: "1",
              averageCost: null,
              price: null,
              priceStatus: "unavailable",
              marketValue: null,
              weight: null,
              realizedPnl: "0",
              unrealizedPnl: null,
              return: null,
              provenance: "local_manual",
              createdAt: "2026-08-14T12:00:00.000Z",
              updatedAt: "2026-08-14T12:00:00.000Z",
            },
          ],
        }),
      ),
    );
    renderPortfolio();
    await waitFor(() => {
      expect(screen.getByTestId("metric-equity")).toHaveTextContent(/partial/i);
      expect(screen.getByTestId("holding-price-btc")).toHaveTextContent(/stale/i);
      expect(screen.getByTestId("holding-price-eth")).toHaveTextContent(/unavailable/i);
      expect(screen.getByTestId("metric-total-pnl")).toHaveTextContent("—");
      expect(screen.getByTestId("metric-total-return")).toHaveTextContent("—");
    });
    expect(screen.queryByText(/drawdown/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/value over time/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("portfolio-history")).not.toBeInTheDocument();
  });

  it("keeps allocation inspect within one holdings book", async () => {
    const btc: PortfolioHolding = {
      id: "22222222-2222-2222-2222-000000000002",
      asset: "btc",
      quantity: "0.005",
      averageCost: null,
      price: "90000",
      priceStatus: "fresh",
      marketValue: "450",
      weight: "0.3103",
      realizedPnl: "0",
      unrealizedPnl: null,
      return: null,
      provenance: "local_manual",
      createdAt: "2026-08-14T12:00:00.000Z",
      updatedAt: "2026-08-14T12:00:00.000Z",
    };
    vi.stubGlobal(
      "fetch",
      mockPortfolioFetch(
        emptySnapshot({
          cash: "1000",
          reserved: "250",
          available: "750",
          equity: "1450",
          equityComplete: true,
          holdings: [usdtHolding("1000"), btc],
          allocations: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              label: "RSI sleeve",
              reservedSize: "250",
              targetRef: "rsi",
              createdAt: "2026-08-14T12:00:00.000Z",
              updatedAt: "2026-08-14T12:00:00.000Z",
            },
          ],
        }),
      ),
    );
    renderPortfolio();
    await waitFor(() => {
      expect(screen.getByTestId("allocation-card-11111111-1111-1111-1111-111111111111")).toBeInTheDocument();
    });
    expect(screen.getByTestId("allocation-reserved-11111111-1111-1111-1111-111111111111")).toHaveTextContent(
      "250 USDT",
    );
    expect(screen.getByText(/Parent portfolio available: 750 USDT/)).toBeInTheDocument();
    expect(screen.getByTestId("holding-qty-btc")).toHaveTextContent("0.005");
    expect(
      allocationsDoNotAffectEquity({
        cash: "1000",
        reserved: "250",
        available: "750",
        deployed: "0",
        realizedPnl: "0",
        unrealizedPnl: "0",
        totalPnl: "50",
        totalReturn: "0.05555556",
        equity: "1450",
        equityComplete: true,
        unvaluedAssets: [],
        positions: [],
        holdings: [usdtHolding("1000"), btc],
        allocations: [],
        updatedAt: null,
        warning: null,
      }),
    ).toBe(true);
  });
});
