import type { BacktestRun } from "../../services/backtestApi";
import { formatRateAsPercent } from "../../services/backtestApi";

interface Props {
  runs: BacktestRun[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

function formatPair(symbol: string): string {
  const parts = symbol.toLowerCase().split("_");
  if (parts.length === 2) {
    return `${parts[0].toUpperCase()}/${parts[1].toUpperCase()}`;
  }
  return symbol.toUpperCase();
}

function formatShortDate(ms: number): string {
  return new Date(ms).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function BacktestRunList({ runs, selectedId, onSelect, onDelete }: Props) {
  return (
    <section className="backtest-run-list" aria-labelledby="backtest-runs-title">
      <h3 id="backtest-runs-title">Recent Backtests</h3>
      {runs.length === 0 ? (
        <p className="hint">No saved runs yet.</p>
      ) : (
        <ul className="backtest-run-items">
          {runs.map((r) => {
            const ret = formatRateAsPercent(r.summary?.returnPct, {
              signed: true,
              digits: 1,
            });
            const ddAbs =
              r.summary?.maxDrawdownPct == null
                ? null
                : Math.abs(Number(r.summary.maxDrawdownPct));
            const dd =
              ddAbs == null || !Number.isFinite(ddAbs)
                ? null
                : `Max DD ${formatRateAsPercent(-ddAbs, { signed: true, digits: 1 })}`;
            const meta =
              r.summary != null
                ? [ret !== "—" ? ret : null, dd].filter(Boolean).join(" · ")
                : "";
            return (
              <li
                key={r.id}
                className={
                  r.id === selectedId
                    ? "backtest-run-item is-selected"
                    : "backtest-run-item"
                }
              >
                <button
                  type="button"
                  className="backtest-run-select"
                  onClick={() => onSelect(r.id)}
                >
                  <span className="backtest-run-title">
                    {formatPair(r.symbol)} · {r.timeframe} ·{" "}
                    {formatShortDate(r.startTime)}–{formatShortDate(r.endTime)}
                  </span>
                  <span className="backtest-run-meta">
                    {r.strategyId}
                    {r.status === "completed" && meta
                      ? ` · ${meta}`
                      : r.status === "failed"
                        ? ` · ${r.errorCode ?? "failed"}`
                        : r.status !== "completed"
                          ? ` · ${r.status}`
                          : null}
                  </span>
                </button>
                <button
                  type="button"
                  className="danger backtest-run-delete"
                  onClick={() => onDelete(r.id)}
                  aria-label={`Delete backtest ${formatPair(r.symbol)} ${r.timeframe}`}
                >
                  Delete
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
