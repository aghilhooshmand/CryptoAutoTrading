import { useCallback, useEffect, useState } from "react";
import {
  type BacktestDecision,
  type BacktestRun,
  type BacktestTrade,
  type CreateBacktestRequest,
  createBacktestRun,
  deleteBacktestRun,
  getBacktestDecisions,
  getBacktestRun,
  getBacktestTrades,
  listBacktestRuns,
} from "../../services/backtestApi";

export function useBacktest() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selected, setSelected] = useState<BacktestRun | null>(null);
  const [trades, setTrades] = useState<BacktestTrade[]>([]);
  const [decisions, setDecisions] = useState<BacktestDecision[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeComparisonOrigin, setIncludeComparisonOrigin] = useState(false);

  const refreshList = useCallback(async () => {
    const res = await listBacktestRuns(20, undefined, {
      includeComparisonOrigin,
    });
    setRuns(res.runs);
  }, [includeComparisonOrigin]);

  useEffect(() => {
    void refreshList().catch(() => {
      /* ignore initial */
    });
  }, [refreshList]);

  const runBacktest = useCallback(
    async (body: CreateBacktestRequest) => {
      setBusy(true);
      setError(null);
      try {
        const run = await createBacktestRun(body);
        setSelected(run);
        const [t, d] = await Promise.all([
          getBacktestTrades(run.id),
          getBacktestDecisions(run.id),
        ]);
        setTrades(t.trades);
        setDecisions(d.decisions);
        await refreshList();
        return run;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Backtest failed");
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [refreshList],
  );

  const selectRun = useCallback(async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const run = await getBacktestRun(id);
      setSelected(run);
      const [t, d] = await Promise.all([
        getBacktestTrades(id),
        getBacktestDecisions(id),
      ]);
      setTrades(t.trades);
      setDecisions(d.decisions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run");
    } finally {
      setBusy(false);
    }
  }, []);

  const removeRun = useCallback(
    async (id: string) => {
      setBusy(true);
      setError(null);
      try {
        await deleteBacktestRun(id);
        if (selected?.id === id) {
          setSelected(null);
          setTrades([]);
          setDecisions([]);
        }
        await refreshList();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      } finally {
        setBusy(false);
      }
    },
    [refreshList, selected?.id],
  );

  return {
    runs,
    selected,
    trades,
    decisions,
    busy,
    error,
    includeComparisonOrigin,
    setIncludeComparisonOrigin,
    runBacktest,
    selectRun,
    removeRun,
    refreshList,
  };
}
