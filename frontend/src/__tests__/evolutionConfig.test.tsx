import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExperimentConfigForm } from "../features/evolution/ExperimentConfigForm";
import { ExperimentProgress } from "../features/evolution/ExperimentProgress";

describe("evolution config", () => {
  it("rejects empty leaves before start", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<ExperimentConfigForm onStart={onStart} />);
    // uncheck all leaves
    const boxes = screen.getByTestId("evolution-leaves").querySelectorAll("input");
    for (const box of boxes) {
      if ((box as HTMLInputElement).checked) {
        await user.click(box);
      }
    }
    await user.click(screen.getByTestId("evolution-start-btn"));
    expect(screen.getByTestId("evolution-config-error")).toHaveTextContent(/leaf/i);
    expect(onStart).not.toHaveBeenCalled();
  });

  it("calls onStart with fitnessId and splits", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<ExperimentConfigForm onStart={onStart} />);
    await user.click(screen.getByTestId("evolution-start-btn"));
    expect(onStart).toHaveBeenCalled();
    const body = onStart.mock.calls[0][0];
    expect(body.fitnessId).toBe("net_minus_bh");
    expect(body.populationSize).toBeGreaterThanOrEqual(2);
    expect(body.paramAlternatives).toBeDefined();
    expect(body.paramAlternatives["rsi.period"]).toContain(14);
  });

  it("rejects empty param alternatives for selected leaf", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<ExperimentConfigForm onStart={onStart} />);
    // uncheck all RSI period options
    for (const opt of [7, 10, 14, 21]) {
      const el = screen.getByTestId(`evolution-param-rsi.period-${opt}`);
      if ((el as HTMLInputElement).checked) await user.click(el);
    }
    await user.click(screen.getByTestId("evolution-start-btn"));
    expect(screen.getByTestId("evolution-config-error")).toHaveTextContent(/alternative/i);
    expect(onStart).not.toHaveBeenCalled();
  });
});

describe("evolution progress", () => {
  it("renders generation chart points", () => {
    render(
      <ExperimentProgress
        experiment={{
          id: "exp_1",
          status: "running",
          generations: [
            { generation: 0, fitnessMax: 1, fitnessAvg: 0.5, bestPhenotype: "rsi(period=14)" },
            { generation: 1, fitnessMax: 2, fitnessAvg: 0.8, bestPhenotype: "rsi(period=7)" },
          ],
        }}
      />,
    );
    expect(screen.getByTestId("evolution-fitness-chart")).toBeInTheDocument();
    expect(screen.getByTestId("evolution-generations-table")).toHaveTextContent("rsi(period=7)");
  });
});
