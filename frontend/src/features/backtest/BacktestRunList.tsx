import type { BacktestRun } from "../../services/backtestApi";

interface Props {
  runs: BacktestRun[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function BacktestRunList({ runs, selectedId, onSelect, onDelete }: Props) {
  return (
    <section className="backtest-run-list" aria-labelledby="backtest-runs-title">
      <h3 id="backtest-runs-title">Saved backtests</h3>
      {runs.length === 0 ? (
        <p>No saved runs yet.</p>
      ) : (
        <ul>
          {runs.map((r) => (
            <li key={r.id} className={r.id === selectedId ? "selected" : undefined}>
              <button type="button" onClick={() => onSelect(r.id)}>
                {r.symbol} {r.timeframe} — {r.status}
                {r.summary?.netPnl != null ? ` · PnL ${r.summary.netPnl}` : ""}
              </button>
              <button type="button" className="danger" onClick={() => onDelete(r.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
