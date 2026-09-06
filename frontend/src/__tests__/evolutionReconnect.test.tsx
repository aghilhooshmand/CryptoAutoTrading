import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvolutionPage } from "../features/evolution/EvolutionPage";

vi.mock("../features/evolution/evolutionApi", () => ({
  listExperiments: vi.fn(),
  getExperiment: vi.fn(),
  createExperiment: vi.fn(),
  cancelExperiment: vi.fn(),
  freezeExperiment: vi.fn(),
}));

import * as api from "../features/evolution/evolutionApi";

describe("evolution reconnect list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listExperiments).mockResolvedValue([
      { id: "exp_abc", status: "running", bestPhenotype: null },
      { id: "exp_done", status: "completed", bestPhenotype: "rsi(period=14)" },
    ]);
    vi.mocked(api.getExperiment).mockResolvedValue({
      id: "exp_abc",
      status: "running",
      generations: [{ generation: 0, fitnessMax: 1, bestPhenotype: "rsi(period=7)" }],
    });
  });

  it("loads recent experiments and resumes poll on select", async () => {
    const user = userEvent.setup();
    render(<EvolutionPage />);
    await waitFor(() => {
      expect(screen.getByTestId("evolution-recent-select")).toBeInTheDocument();
    });
    expect(api.listExperiments).toHaveBeenCalled();
    await user.selectOptions(screen.getByTestId("evolution-recent-select"), "exp_abc");
    await waitFor(() => {
      expect(api.getExperiment).toHaveBeenCalledWith("exp_abc");
    });
    expect(await screen.findByTestId("evolution-status")).toHaveTextContent("running");
  });
});
