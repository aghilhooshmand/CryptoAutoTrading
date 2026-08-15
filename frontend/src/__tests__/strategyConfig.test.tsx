import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";

import {
  StrategyConfigFields,
  defaultStrategyConfig,
  type StrategyConfigValue,
} from "../features/strategy/StrategyConfigFields";
import {
  validateStrategyParamsClient,
  type StrategyInfo,
} from "../services/strategiesApi";

const BOLLINGER_FIXTURE: StrategyInfo = {
  id: "bollinger_bands",
  displayName: "Bollinger Bands",
  aliases: [],
  parameters: [
    {
      name: "period",
      type: "integer",
      label: "Period",
      default: 20,
      minimum: 2,
    },
    {
      name: "stdDev",
      type: "decimal_string",
      label: "Std deviations",
      default: "2.0",
      minimum: 0,
      exclusiveMinimum: true,
    },
  ],
  constraints: [],
};

const RSI_FIXTURE: StrategyInfo = {
  id: "rsi",
  displayName: "RSI",
  aliases: [],
  parameters: [
    { name: "period", type: "integer", label: "RSI period", default: 14, minimum: 2 },
    {
      name: "overbought",
      type: "integer",
      label: "Overbought",
      default: 70,
      minimum: 1,
      maximum: 99,
    },
    {
      name: "oversold",
      type: "integer",
      label: "Oversold",
      default: 30,
      minimum: 1,
      maximum: 99,
    },
  ],
  constraints: [
    {
      code: "oversold_lt_overbought",
      message: "Oversold threshold must be less than overbought threshold.",
      fields: ["oversold", "overbought"],
    },
  ],
};

const MACD_FIXTURE: StrategyInfo = {
  id: "macd",
  displayName: "MACD",
  aliases: [],
  parameters: [
    { name: "fastPeriod", type: "integer", label: "Fast period", default: 12, minimum: 1 },
    { name: "slowPeriod", type: "integer", label: "Slow period", default: 26, minimum: 2 },
    {
      name: "signalPeriod",
      type: "integer",
      label: "Signal period",
      default: 9,
      minimum: 1,
    },
  ],
  constraints: [
    {
      code: "fast_lt_slow",
      message: "Fast period must be less than slow period.",
      fields: ["fastPeriod", "slowPeriod"],
    },
  ],
};

const BREAKOUT_FIXTURE: StrategyInfo = {
  id: "breakout",
  displayName: "Breakout",
  aliases: [],
  parameters: [
    { name: "lookback", type: "integer", label: "Lookback", default: 20, minimum: 2 },
  ],
  constraints: [],
};

vi.mock("../services/strategiesApi", async () => {
  const actual = await vi.importActual<typeof import("../services/strategiesApi")>(
    "../services/strategiesApi",
  );
  return {
    ...actual,
    listStrategies: vi.fn(async () => actual.FALLBACK_STRATEGIES),
  };
});

function Harness({
  initial,
  preferredStrategy,
}: {
  initial?: StrategyConfigValue;
  preferredStrategy?: StrategyConfigValue | null;
}) {
  const [value, setValue] = useState<StrategyConfigValue>(
    initial ?? defaultStrategyConfig(),
  );
  return (
    <StrategyConfigFields
      value={value}
      onChange={setValue}
      preferredStrategy={preferredStrategy}
    />
  );
}

describe("strategy config fields", () => {
  it("defaults Dual EMA periods to 9 and 21", async () => {
    render(<Harness />);
    await waitFor(() => {
      expect(screen.getByTestId("strategy-id")).toHaveAttribute(
        "data-strategy-id",
        "dual_ema",
      );
    });
    expect(screen.getByTestId("strategy-id")).toHaveTextContent("Dual EMA");
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(9);
    expect(screen.getByTestId("strategy-param-slowPeriod")).toHaveValue(21);
  });

  it("shows fast < slow cross-field message", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-param-fastPeriod"));
    await user.clear(screen.getByTestId("strategy-param-fastPeriod"));
    await user.type(screen.getByTestId("strategy-param-fastPeriod"), "30");
    expect(screen.getByTestId("strategy-param-error")).toHaveTextContent(
      "Fast period must be less than slow period.",
    );
  });

  it("lists all fallback strategies in the selector", async () => {
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-id"));
    const select = screen.getByTestId("strategy-id");
    expect(select.tagName).toBe("SELECT");
    expect(select).toHaveTextContent("Dual EMA");
    expect(select).toHaveTextContent("RSI");
    expect(select).toHaveTextContent("MACD");
    expect(select).toHaveTextContent("Bollinger Bands");
    expect(select).toHaveTextContent("Breakout");
  });

  it("switches to RSI defaults when selected", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-id"));
    await user.selectOptions(screen.getByTestId("strategy-id"), "rsi");
    expect(screen.getByTestId("strategy-param-period")).toHaveValue(14);
    expect(screen.getByTestId("strategy-param-overbought")).toHaveValue(70);
    expect(screen.getByTestId("strategy-param-oversold")).toHaveValue(30);
  });

  it("restores preferred Settings params when selecting that Rule again", async () => {
    const user = userEvent.setup();
    const preferred = {
      strategyId: "dual_ema",
      strategyParams: { fastPeriod: 10, slowPeriod: 21 },
    };
    render(
      <Harness
        initial={preferred}
        preferredStrategy={preferred}
      />,
    );
    await waitFor(() => screen.getByTestId("strategy-id"));
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);

    await user.selectOptions(screen.getByTestId("strategy-id"), "rsi");
    expect(screen.getByTestId("strategy-param-period")).toHaveValue(14);

    await user.selectOptions(screen.getByTestId("strategy-id"), "dual_ema");
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);
    expect(screen.getByTestId("strategy-param-slowPeriod")).toHaveValue(21);
  });

  it("remembers draft params when switching Rule away and back", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-param-fastPeriod"));
    await user.clear(screen.getByTestId("strategy-param-fastPeriod"));
    await user.type(screen.getByTestId("strategy-param-fastPeriod"), "10");
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);

    await user.selectOptions(screen.getByTestId("strategy-id"), "rsi");
    expect(screen.getByTestId("strategy-param-period")).toHaveValue(14);

    await user.selectOptions(screen.getByTestId("strategy-id"), "dual_ema");
    expect(screen.getByTestId("strategy-param-fastPeriod")).toHaveValue(10);
  });
});

describe("validateStrategyParamsClient decimal_string and RSI", () => {
  it("accepts decimal_string values without requiring integers", () => {
    expect(
      validateStrategyParamsClient(BOLLINGER_FIXTURE, {
        period: 20,
        stdDev: "2.0",
      }),
    ).toBeNull();
    expect(
      validateStrategyParamsClient(BOLLINGER_FIXTURE, {
        period: 20,
        stdDev: "1.5",
      }),
    ).toBeNull();
  });

  it("rejects stdDev of 0 when exclusiveMinimum is set", () => {
    expect(
      validateStrategyParamsClient(BOLLINGER_FIXTURE, {
        period: 20,
        stdDev: "0",
      }),
    ).toMatch(/> 0/);
  });

  it("shows oversold < overbought message for RSI", () => {
    expect(
      validateStrategyParamsClient(RSI_FIXTURE, {
        period: 14,
        overbought: 30,
        oversold: 70,
      }),
    ).toBe("Oversold threshold must be less than overbought threshold.");
  });

  it("shows fast < slow message for MACD", () => {
    expect(
      validateStrategyParamsClient(MACD_FIXTURE, {
        fastPeriod: 26,
        slowPeriod: 12,
        signalPeriod: 9,
      }),
    ).toBe("Fast period must be less than slow period.");
  });
});

describe("decimal_string field rendering", () => {
  it("renders decimal_string as text and preserves spelling in controlled value", async () => {
    const user = userEvent.setup();

    function DecimalHarness() {
      const [value, setValue] = useState<StrategyConfigValue>({
        strategyId: "bollinger_bands",
        strategyParams: { period: 20, stdDev: "2.0" },
      });
      return (
        <>
          <StrategyConfigFields value={value} onChange={setValue} />
          <pre data-testid="payload">{JSON.stringify(value.strategyParams)}</pre>
        </>
      );
    }

    render(<DecimalHarness />);
    await waitFor(() => screen.getByTestId("strategy-param-stdDev"));
    const input = screen.getByTestId("strategy-param-stdDev");
    expect(input).toHaveAttribute("data-param-type", "decimal_string");
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("2.0");

    await user.clear(input);
    await user.type(input, "1.5");
    expect(screen.getByTestId("payload")).toHaveTextContent('"stdDev":"1.5"');
  });

  it("renders Breakout lookback default from fallback catalog", async () => {
    render(<Harness />);
    await waitFor(() => screen.getByTestId("strategy-id"));
    const user = userEvent.setup();
    await user.selectOptions(screen.getByTestId("strategy-id"), "breakout");
    expect(screen.getByTestId("strategy-param-lookback")).toHaveValue(20);
  });
});
