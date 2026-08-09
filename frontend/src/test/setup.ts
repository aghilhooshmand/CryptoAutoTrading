import "@testing-library/jest-dom/vitest";
import React from "react";
import { vi } from "vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverStub);

vi.stubGlobal(
  "matchMedia",
  vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
);

// Avoid lightweight-charts canvas/jsdom issues in unit tests, but preserve
// visibility rules used for selection/error invalidation.
vi.mock("../features/market-data/CandleChart", () => ({
  CandleChart: (props: {
    candles?: unknown[];
    interval?: string;
    statusMessage?: string | null;
    loading?: boolean;
    onIntervalChange?: (interval: string) => void;
  }) => {
    const showChart =
      !props.loading &&
      !props.statusMessage &&
      (props.candles?.length ?? 0) > 0;
    return React.createElement(
      "div",
      null,
      props.loading
        ? React.createElement("p", null, "Loading history…")
        : null,
      props.statusMessage
        ? React.createElement(
            "p",
            { className: "market-error", role: "status" },
            props.statusMessage,
          )
        : null,
      !props.loading && !props.statusMessage && (props.candles?.length ?? 0) === 0
        ? React.createElement("p", null, "No candlestick data available.")
        : null,
      React.createElement("div", {
        "data-testid": "candle-chart",
        hidden: !showChart,
      }),
    );
  },
}));
