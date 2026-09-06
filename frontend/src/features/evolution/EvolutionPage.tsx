import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelExperiment,
  createExperiment,
  freezeExperiment,
  getExperiment,
  type Experiment,
  type ExperimentConfigBody,
} from "./evolutionApi";
import { ExperimentConfigForm } from "./ExperimentConfigForm";
import { ExperimentProgress } from "./ExperimentProgress";
import { FreezeStrategyForm } from "./FreezeStrategyForm";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function EvolutionPage() {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current != null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refresh = useCallback(async (id: string) => {
    const exp = await getExperiment(id);
    setExperiment(exp);
    if (TERMINAL.has(exp.status)) {
      stopPoll();
      setBusy(false);
    }
  }, [stopPoll]);

  useEffect(() => () => stopPoll(), [stopPoll]);

  async function onStart(body: ExperimentConfigBody) {
    setError(null);
    setBusy(true);
    stopPoll();
    try {
      const created = await createExperiment(body);
      setExperiment(created);
      pollRef.current = window.setInterval(() => {
        void refresh(created.id).catch((err) => {
          setError(err instanceof Error ? err.message : "Poll failed");
          stopPoll();
          setBusy(false);
        });
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Start failed");
      setBusy(false);
    }
  }

  async function onCancel() {
    if (!experiment) return;
    try {
      await cancelExperiment(experiment.id);
      await refresh(experiment.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    }
  }

  const terminal = experiment ? TERMINAL.has(experiment.status) : false;
  const canFreeze = Boolean(terminal && experiment?.bestPhenotype);

  return (
    <div data-testid="evolution-page">
      <h2 className="auto-trading-panel-title">Evolution (UGE lab)</h2>
      <p className="auto-trading-lede">
        Offline Grammatical Evolution over Torque programs. Watch each generation,
        then freeze the best phenotype into the strategy list for Backtest /
        Simulation. This lab never places Real orders.
      </p>
      <ExperimentConfigForm
        disabled={busy && !terminal}
        onStart={onStart}
        onCancel={onCancel}
        canCancel={Boolean(experiment && !terminal)}
      />
      {error ? (
        <p className="form-error" role="alert" data-testid="evolution-page-error">
          {error}
        </p>
      ) : null}
      <ExperimentProgress experiment={experiment} />
      {canFreeze ? (
        <FreezeStrategyForm
          onFreeze={async (name) => {
            if (!experiment) return;
            const entry = await freezeExperiment(experiment.id, name);
            setError(null);
            void entry;
          }}
        />
      ) : null}
    </div>
  );
}
