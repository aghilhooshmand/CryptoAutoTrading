import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BacktestConfigForm } from "../features/backtest/BacktestConfigForm";

vi.mock("../services/settingsApi", () => ({
  getSettings: vi.fn(async () => {
    throw new Error("skip settings");
  }),
}));

vi.mock("../services/ugeApi", () => ({
  listFrozenArtifacts: vi.fn(async () => [
    {
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      phenotype: "rsi(period=14, oversold=30, overbought=70)",
      trainFitness: 1.25,
    },
  ]),
}));

vi.mock("../services/strategiesApi", async () => {
  const actual = await vi.importActual<typeof import("../services/strategiesApi")>(
    "../services/strategiesApi",
  );
  return {
    ...actual,
    listStrategies: vi.fn(async () => [
      ...actual.FALLBACK_STRATEGIES,
      {
        id: "torque_phenotype",
        displayName: "Torque phenotype (UGE / frozen)",
        aliases: [],
        parameters: [
          {
            name: "phenotype",
            type: "string" as const,
            label: "Torque phenotype",
            default: "rsi(period=14, oversold=30, overbought=70)",
          },
        ],
        constraints: [],
      },
    ]),
  };
});

describe("Backtest frozen phenotype select", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads a frozen phenotype into torque_phenotype strategy", async () => {
    const user = userEvent.setup();
    render(<BacktestConfigForm onSubmit={vi.fn()} />);
    const picker = await screen.findByTestId("frozen-phenotype-picker");
    expect(picker).toBeInTheDocument();
    const select = picker.querySelector("select");
    expect(select).toBeTruthy();
    await user.selectOptions(select!, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await waitFor(() => {
      expect(screen.getByTestId("strategy-id")).toHaveAttribute(
        "data-strategy-id",
        "torque_phenotype",
      );
    });
    expect(screen.getByTestId("strategy-param-phenotype")).toHaveValue(
      "rsi(period=14, oversold=30, overbought=70)",
    );
  });
});
