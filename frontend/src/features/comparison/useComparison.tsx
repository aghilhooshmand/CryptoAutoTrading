import { useCallback, useEffect, useState } from "react";
import {
  type CreateComparisonRequest,
  type StrategyComparison,
  createComparison,
  deleteComparison,
  getComparison,
  listComparisons,
} from "../../services/comparisonApi";

export function useComparison() {
  const [comparisons, setComparisons] = useState<StrategyComparison[]>([]);
  const [selected, setSelected] = useState<StrategyComparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshList = useCallback(async () => {
    const res = await listComparisons(20);
    setComparisons(res.comparisons);
  }, []);

  useEffect(() => {
    void refreshList().catch(() => {
      /* ignore initial */
    });
  }, [refreshList]);

  const runComparison = useCallback(
    async (body: CreateComparisonRequest) => {
      setBusy(true);
      setError(null);
      try {
        const comparison = await createComparison(body);
        setSelected(comparison);
        await refreshList();
        return comparison;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Comparison failed");
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [refreshList],
  );

  const selectComparison = useCallback(async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const comparison = await getComparison(id);
      setSelected(comparison);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load comparison");
    } finally {
      setBusy(false);
    }
  }, []);

  const removeComparison = useCallback(
    async (id: string) => {
      setBusy(true);
      setError(null);
      try {
        await deleteComparison(id);
        if (selected?.id === id) {
          setSelected(null);
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
    comparisons,
    selected,
    busy,
    error,
    runComparison,
    selectComparison,
    removeComparison,
    refreshList,
  };
}
