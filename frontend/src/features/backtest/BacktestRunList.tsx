import type { BacktestRun } from "../../services/backtestApi";

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

function formatReturnPct(value: string | undefined): string | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  const pct = n * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function formatDrawdownPct(value: string | undefined): string | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  const pct = Math.abs(n) * 100;
  return `Max DD -${pct.toFixed(1)}%`;
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
            const ret = formatReturnPct(r.summary?.returnPct);
            const dd = formatDrawdownPct(r.summary?.maxDrawdownPct);
            const meta = [ret, dd].filter(Boolean).join(" · ");
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
                    {r.status === "completed" && meta
                      ? meta
                      : r.status === "failed"
                        ? r.errorCode ?? "failed"
                        : r.status}
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
