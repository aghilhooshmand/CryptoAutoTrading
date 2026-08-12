import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutoTradingPage } from "../pages/AutoTradingPage";
import { ComparisonConfigForm } from "../features/comparison/ComparisonConfigForm";
import {
  FALLBACK_STRATEGIES,
  validateStrategyParamsClient,
} from "../services/strategiesApi";

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/strategies")) {
      return new Response(JSON.stringify({ strategies: FALLBACK_STRATEGIES }), {
        status: 200,
      });
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

describe("comparison per-leg params", () => {
  beforeEach(() => {
    cleanup();
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("editing one leg does not change another leg’s strategy id", async () => {
    const user = userEvent.setup();
    render(<AutoTradingPage />);
    await user.click(screen.getByRole("tab", { name: /^Comparison$/i }));

    const leg0 = screen.getByTestId("comparison-leg-0");
    const leg1 = screen.getByTestId("comparison-leg-1");
    const leg0Select = leg0.querySelector("select") as HTMLSelectElement;
    const leg1Select = leg1.querySelector("select") as HTMLSelectElement;
    const leg1Before = leg1Select.value;

    await user.selectOptions(leg0Select, "macd");
    expect(leg0Select.value).toBe("macd");
    expect(leg1Select.value).toBe(leg1Before);
  });

  it("surfaces RSI oversold/overbought constraint client-side", () => {
    const rsi = FALLBACK_STRATEGIES.find((s) => s.id === "rsi");
    expect(rsi).toBeTruthy();
    const msg = validateStrategyParamsClient(rsi!, {
      period: 14,
      overbought: 20,
      oversold: 80,
    });
    expect(msg).toMatch(/oversold|overbought/i);
  });
});

describe("comparison form payload shape", () => {
  beforeEach(() => {
    cleanup();
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("builds a two-leg create payload with shared capital", async () => {
    const user = userEvent.setup();
    let captured: unknown = null;
    const { container } = render(
      <ComparisonConfigForm
        onSubmit={(body) => {
          captured = body;
        }}
      />,
    );

    const start = container.querySelector(
      'input[type="datetime-local"]',
    ) as HTMLInputElement;
    const end = container.querySelectorAll(
      'input[type="datetime-local"]',
    )[1] as HTMLInputElement;
    await user.type(start, "2026-01-01T00:00");
    await user.type(end, "2026-01-05T00:00");
    await user.click(screen.getByRole("button", { name: /Run Comparison/i }));

    expect(captured).toBeTruthy();
    const body = captured as {
      legs: { strategyId: string }[];
      startingCapital: string;
    };
    expect(body.legs.length).toBe(2);
    expect(body.startingCapital).toBe("1000");
  });
});
