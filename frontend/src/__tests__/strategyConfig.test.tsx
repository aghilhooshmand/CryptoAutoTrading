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

vi.mock("../services/strategiesApi", async () => {
  const actual = await vi.importActual<typeof import("../services/strategiesApi")>(
    "../services/strategiesApi",
  );
  return {
    ...actual,
    listStrategies: vi.fn(async () => actual.FALLBACK_STRATEGIES),
  };
});

function Harness({ initial }: { initial?: StrategyConfigValue }) {
  const [value, setValue] = useState<StrategyConfigValue>(
    initial ?? defaultStrategyConfig(),
  );
  return <StrategyConfigFields value={value} onChange={setValue} />;
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
});

describe("decimal_string field rendering", () => {
  it("renders decimal_string as text and preserves spelling in controlled value", async () => {
    const { listStrategies } = await import("../services/strategiesApi");
    vi.mocked(listStrategies).mockResolvedValueOnce([
      ...((await vi.importActual<typeof import("../services/strategiesApi")>(
        "../services/strategiesApi",
      )).FALLBACK_STRATEGIES),
      BOLLINGER_FIXTURE,
    ]);

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

    const user = userEvent.setup();
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
});
