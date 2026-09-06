import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelExperiment,
  createExperiment,
  freezeExperiment,
  getExperiment,
  listExperiments,
  type Experiment,
  type ExperimentConfigBody,
} from "./evolutionApi";
import { ExperimentConfigForm } from "./ExperimentConfigForm";
import { ExperimentProgress } from "./ExperimentProgress";
import { FreezeStrategyForm } from "./FreezeStrategyForm";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function EvolutionPage() {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [recent, setRecent] = useState<Experiment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current != null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const loadRecent = useCallback(async () => {
    try {
      const list = await listExperiments();
      setRecent(list.slice(0, 20));
    } catch {
      /* list is best-effort for reconnect */
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPoll();
      pollRef.current = window.setInterval(() => {
        void getExperiment(id)
          .then((exp) => {
            setExperiment(exp);
            if (TERMINAL.has(exp.status)) {
              stopPoll();
              setBusy(false);
              void loadRecent();
            }
          })
          .catch((err) => {
            setError(err instanceof Error ? err.message : "Poll failed");
            stopPoll();
            setBusy(false);
          });
      }, 1000);
    },
    [loadRecent, stopPoll],
  );

  const refresh = useCallback(
    async (id: string) => {
      const exp = await getExperiment(id);
      setExperiment(exp);
      if (TERMINAL.has(exp.status)) {
        stopPoll();
        setBusy(false);
      }
    },
    [stopPoll],
  );

  useEffect(() => {
    void loadRecent();
    return () => stopPoll();
  }, [loadRecent, stopPoll]);

  async function onStart(body: ExperimentConfigBody) {
    setError(null);
    setBusy(true);
    stopPoll();
    try {
      const created = await createExperiment(body);
      setExperiment(created);
      setBusy(true);
      startPolling(created.id);
      void loadRecent();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Start failed");
      setBusy(false);
    }
  }

  async function onSelectExperiment(id: string) {
    setError(null);
    try {
      const exp = await getExperiment(id);
      setExperiment(exp);
      if (!TERMINAL.has(exp.status)) {
        setBusy(true);
        startPolling(id);
      } else {
        stopPoll();
        setBusy(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    }
  }

  async function onCancel() {
    if (!experiment) return;
    try {
      await cancelExperiment(experiment.id);
      await refresh(experiment.id);
      void loadRecent();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    }
  }

  const terminal = experiment ? TERMINAL.has(experiment.status) : false;
  const canFreeze = Boolean(terminal && experiment?.bestPhenotype);

  return (
    <div data-testid="evolution-page">
      <section
        className="backtest-config evolution-reconnect"
        data-testid="evolution-recent-list"
        aria-labelledby="evolution-reconnect-title"
      >
        <h3 id="evolution-reconnect-title" className="visually-hidden">
          Recent experiments
        </h3>
        <fieldset className="backtest-fieldset">
          <legend>Recent experiments</legend>
          <p className="field-hint">
            Select a run to resume polling or inspect a finished experiment.
          </p>
          <div className="backtest-field-row evolution-reconnect-row">
            <label>
              Experiment
              <select
                value={experiment?.id ?? ""}
                onChange={(e) => {
                  const id = e.target.value;
                  if (id) void onSelectExperiment(id);
                }}
                data-testid="evolution-recent-select"
              >
                <option value="">— select to resume / inspect —</option>
                {recent.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.id} · {item.status}
                    {item.bestPhenotype
                      ? ` · ${item.bestPhenotype.slice(0, 40)}`
                      : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="evolution-reconnect-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => void loadRecent()}
                data-testid="evolution-recent-refresh"
              >
                Refresh list
              </button>
            </div>
          </div>
        </fieldset>
      </section>

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
            await freezeExperiment(experiment.id, name);
            setError(null);
            void loadRecent();
          }}
        />
      ) : null}
    </div>
  );
}
