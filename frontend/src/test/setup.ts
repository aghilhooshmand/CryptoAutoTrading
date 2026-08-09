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

// Avoid lightweight-charts canvas/jsdom issues in unit tests.
vi.mock("../features/market-data/CandleChart", () => ({
  CandleChart: (props: {
    interval?: string;
    statusMessage?: string | null;
    loading?: boolean;
  }) =>
    React.createElement(
      "div",
      { "data-testid": "candle-chart" },
      props.interval ? React.createElement("span", null, props.interval) : null,
      props.loading
        ? React.createElement("span", null, "Loading history…")
        : null,
      props.statusMessage
        ? React.createElement("span", null, props.statusMessage)
        : null,
    ),
}));
