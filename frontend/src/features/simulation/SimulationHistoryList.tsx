import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import type { HistoryListItem, SessionState } from "../../services/simulationApi";
import { deleteSession, listSessions, rateToPercentLabel } from "../../services/simulationApi";

const PAGE_SIZE = 50;

interface Props {
  refreshKey?: number;
}

export function SimulationHistoryList({ refreshKey = 0 }: Props) {
  const [items, setItems] = useState<HistoryListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [stateFilter, setStateFilter] = useState<SessionState | "">("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(nextOffset = offset) {
    setBusy(true);
    setError(null);
    try {
      const data = await listSessions({
        state: stateFilter || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setItems(data.sessions);
      setTotalCount(data.totalCount);
      setOffset(data.offset);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload on filter/refresh
  }, [stateFilter, refreshKey]);

  async function handleDelete(id: string) {
    const ok = window.confirm(
      "Delete this Simulation session and its journals? This cannot be undone. Portfolio capital is never released by this action.",
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await deleteSession(id);
      await load(offset);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const pageEnd = Math.min(offset + items.length, totalCount);
  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < totalCount;

  return (
    <section
      className="simulation-history-list"
      data-testid="simulation-history-list"
      aria-labelledby="sim-history-title"
    >
      <div className="sim-history-header">
        <h2 id="sim-history-title">Simulation history</h2>
        <label className="sim-history-filter">
          State
          <select
            data-testid="sim-history-state-filter"
            value={stateFilter}
            disabled={busy}
            onChange={(e) => setStateFilter(e.target.value as SessionState | "")}
          >
            <option value="">All</option>
            <option value="CONFIGURED">CONFIGURED</option>
            <option value="RUNNING">RUNNING</option>
            <option value="STOPPING">STOPPING</option>
            <option value="STOPPED">STOPPED</option>
          </select>
        </label>
      </div>

      {error ? (
        <p className="form-error" role="alert" data-testid="sim-history-error">
          {error}
        </p>
      ) : null}

      {items.length === 0 ? (
        <p className="note">No saved Simulations yet.</p>
      ) : (
        <ul className="sim-history-items">
          {items.map((s) => {
            const summary =
              s.finalResultSummary == null
                ? s.state
                : s.finalResultSummary.complete
                  ? `net ${s.finalResultSummary.netPnl ?? "—"} · ${
                      s.finalResultSummary.returnPct != null
                        ? rateToPercentLabel(s.finalResultSummary.returnPct)
                        : "—"
                    }`
                  : "incomplete result";
            const canDelete = s.state === "STOPPED" || s.state === "CONFIGURED";
            return (
              <li key={s.id} className="sim-history-item" data-testid={`sim-history-item-${s.id}`}>
                <Link
                  className="sim-history-link"
                  to={`/auto-trading/simulation/${s.id}`}
                  data-testid={`sim-history-open-${s.id}`}
                >
                  <span className="sim-history-title">
                    {s.symbol} · {s.timeframe} · {s.state}
                  </span>
                  <span className="sim-history-meta">
                    {s.strategyId}
                    {s.createdAt ? ` · ${s.createdAt}` : ""}
                    {` · ${summary}`}
                  </span>
                </Link>
                {canDelete ? (
                  <button
                    type="button"
                    className="danger"
                    data-testid={`sim-history-delete-${s.id}`}
                    disabled={busy}
                    onClick={() => {
                      void handleDelete(s.id);
                    }}
                  >
                    Delete
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      <div className="sim-history-pager" data-testid="sim-history-pager">
        <span data-testid="sim-history-count">
          {totalCount === 0 ? "0 sessions" : `${offset + 1}–${pageEnd} of ${totalCount}`}
        </span>
        <button
          type="button"
          data-testid="sim-history-prev"
          disabled={!canPrev || busy}
          onClick={() => {
            void load(Math.max(0, offset - PAGE_SIZE));
          }}
        >
          Previous
        </button>
        <button
          type="button"
          data-testid="sim-history-next"
          disabled={!canNext || busy}
          onClick={() => {
            void load(offset + PAGE_SIZE);
          }}
        >
          Next
        </button>
      </div>
    </section>
  );
}
