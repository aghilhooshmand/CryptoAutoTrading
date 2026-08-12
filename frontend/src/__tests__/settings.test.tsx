import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AutoTradingPage } from "../pages/AutoTradingPage";
import { SettingsPanel } from "../features/settings/SettingsPanel";
import type { OperatorSettings } from "../services/settingsApi";

const starters: OperatorSettings = {
  symbol: "btc_usdt",
  timeframe: "1h",
  startingCapital: "1000",
  allocatedCapital: "1000",
  maxPositionSize: "1000",
  feeRate: "0.002",
  slippageRate: "0.0005",
  targetNetProfitRate: null,
  maxSessionLossRate: null,
  maxTrades: null,
  strategyId: "dual_ema",
  strategyParams: { fastPeriod: 9, slowPeriod: 21 },
  updatedAt: null,
  source: "starters",
  warning: null,
};

function mockFetch(handlers?: {
  get?: OperatorSettings;
  put?: (body: unknown) => OperatorSettings | { error: { code: string; message: string }; status?: number };
  reset?: OperatorSettings;
}) {
  let saved: OperatorSettings = handlers?.get ?? { ...starters };
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    if (url.includes("/strategies")) {
      return new Response(
        JSON.stringify({
          strategies: [
            {
              id: "dual_ema",
              displayName: "Dual EMA",
              aliases: [],
              parameters: [
                { name: "fastPeriod", type: "int", label: "Fast", default: 9 },
                { name: "slowPeriod", type: "int", label: "Slow", default: 21 },
              ],
              constraints: [],
            },
            {
              id: "rsi",
              displayName: "RSI",
              aliases: [],
              parameters: [
                { name: "period", type: "int", label: "Period", default: 14 },
                { name: "overbought", type: "int", label: "Overbought", default: 70 },
                { name: "oversold", type: "int", label: "Oversold", default: 30 },
              ],
              constraints: [],
            },
          ],
        }),
        { status: 200 },
      );
    }
    if (url.includes("/settings/reset") && method === "POST") {
      saved = handlers?.reset ?? { ...starters, source: "saved", updatedAt: "2026-08-12T00:00:00Z" };
      return new Response(JSON.stringify(saved), { status: 200 });
    }
    if (url.endsWith("/settings") || url.includes("/settings?")) {
      if (method === "PUT") {
        const body = JSON.parse(String(init?.body ?? "{}"));
        if (handlers?.put) {
          const result = handlers.put(body);
          if ("error" in result) {
            return new Response(JSON.stringify({ detail: { error: result.error } }), {
              status: result.status ?? 400,
            });
          }
          saved = result;
          return new Response(JSON.stringify(saved), { status: 200 });
        }
        if (Number(body.maxPositionSize) > Number(body.allocatedCapital)) {
          return new Response(
            JSON.stringify({
              detail: {
                error: {
                  code: "invalid_config",
                  message: "Require 0 < max_position_size <= allocated_capital <= starting_capital",
                },
              },
            }),
            { status: 400 },
          );
        }
        saved = {
          ...saved,
          ...body,
          source: "saved",
          updatedAt: "2026-08-12T12:00:00Z",
          warning: null,
        };
        return new Response(JSON.stringify(saved), { status: 200 });
      }
      return new Response(JSON.stringify(handlers?.get ?? saved), { status: 200 });
    }
    if (url.includes("/comparisons")) {
      return new Response(JSON.stringify({ comparisons: [] }), { status: 200 });
    }
    if (url.includes("/backtest/runs")) {
      return new Response(JSON.stringify({ runs: [] }), { status: 200 });
    }
    if (url.includes("/simulation")) {
      return new Response(JSON.stringify({ session: null }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 404 });
  });
}

describe("Settings panel", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads starters and saves distinctive values", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel />);
    await screen.findByTestId("settings-form");

    const symbol = screen.getByTestId("settings-symbol");
    await user.clear(symbol);
    await user.type(symbol, "eth_usdt");
    await user.click(screen.getByTestId("settings-save"));

    await waitFor(() => {
      expect(screen.getByTestId("settings-status")).toHaveTextContent(/saved/i);
    });
    expect(screen.getByTestId("settings-symbol")).toHaveValue("eth_usdt");
  });

  it("shows fail-closed warning from GET", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        get: {
          ...starters,
          warning: "Saved Settings could not be used. Showing product starters.",
        },
      }),
    );
    render(<SettingsPanel />);
    expect(await screen.findByTestId("settings-warning")).toHaveTextContent(/could not be used/i);
  });

  it("rejects bad nesting on Save and keeps prior values", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel />);
    await screen.findByTestId("settings-form");
    await user.clear(screen.getByTestId("settings-max-pos"));
    await user.type(screen.getByTestId("settings-max-pos"), "9000");
    await user.click(screen.getByTestId("settings-save"));
    expect(await screen.findByTestId("settings-error")).toBeInTheDocument();
    expect(screen.getByTestId("settings-starting")).toHaveValue("1000");
  });

  it("reset restores starters after confirm", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.stubGlobal(
      "fetch",
      mockFetch({
        get: {
          ...starters,
          symbol: "eth_usdt",
          source: "saved",
          updatedAt: "2026-08-12T00:00:00Z",
        },
      }),
    );
    render(<SettingsPanel />);
    await screen.findByTestId("settings-form");
    expect(screen.getByTestId("settings-symbol")).toHaveValue("eth_usdt");
    await user.click(screen.getByTestId("settings-reset"));
    await waitFor(() => {
      expect(screen.getByTestId("settings-symbol")).toHaveValue("btc_usdt");
    });
  });

  it("keeps Save and Reset usable at ~375px width", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    render(<SettingsPanel />);
    await screen.findByTestId("settings-form");
    const save = screen.getByTestId("settings-save");
    const reset = screen.getByTestId("settings-reset");
    expect(save).toBeVisible();
    expect(reset).toBeVisible();
  });
});

describe("Auto Trading Settings tab", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("hosts Settings under Auto Trading without a 4th primary nav", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);
    const tab = await screen.findByRole("tab", { name: "Settings" });
    await user.click(tab);
    expect(await screen.findByTestId("settings-form")).toBeInTheDocument();
  });

  it("preserves unsaved Settings draft across tab switches", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);
    await user.click(await screen.findByRole("tab", { name: "Settings" }));
    await screen.findByTestId("settings-form");
    await user.clear(screen.getByTestId("settings-symbol"));
    await user.type(screen.getByTestId("settings-symbol"), "sol_usdt");
    await user.click(screen.getByRole("tab", { name: "Simulation" }));
    await user.click(screen.getByRole("tab", { name: "Settings" }));
    expect(screen.getByTestId("settings-symbol")).toHaveValue("sol_usdt");
  });
});

describe("settings side effects", () => {
  it("Save and Reset do not call create session/run/comparison endpoints", async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<SettingsPanel />);
    await screen.findByTestId("settings-form");
    await user.click(screen.getByTestId("settings-save"));
    await user.click(screen.getByTestId("settings-reset"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.some((u) => u.includes("/simulation/sessions"))).toBe(false);
    expect(urls.some((u) => u.includes("/backtest/runs") && (u.includes("POST") || false))).toBe(
      false,
    );
    const methods = fetchMock.mock.calls.map((c) => (c[1]?.method ?? "GET").toUpperCase());
    const postPuts = fetchMock.mock.calls.filter((c) => {
      const m = (c[1]?.method ?? "GET").toUpperCase();
      return m === "POST" || m === "PUT";
    });
    for (const call of postPuts) {
      const u = String(call[0]);
      expect(u.includes("/settings")).toBe(true);
    }
    void methods;
    void within;
    cleanup();
    vi.unstubAllGlobals();
  });
});
