import type { StrategyComparison } from "../../services/comparisonApi";

interface Props {
  comparisons: StrategyComparison[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function ComparisonList({
  comparisons,
  selectedId,
  onSelect,
  onDelete,
}: Props) {
  return (
    <section className="backtest-run-list" aria-labelledby="comparison-list-title">
      <h3 id="comparison-list-title">Recent Comparisons</h3>
      {comparisons.length === 0 ? (
        <p className="hint">No saved comparisons yet.</p>
      ) : (
        <ul className="backtest-run-items">
          {comparisons.map((c) => (
            <li
              key={c.id}
              className={
                c.id === selectedId
                  ? "backtest-run-item is-selected"
                  : "backtest-run-item"
              }
            >
              <button
                type="button"
                className="backtest-run-select"
                onClick={() => onSelect(c.id)}
              >
                <span className="backtest-run-title">
                  {c.symbol} · {c.timeframe} · {c.legs.length} legs
                </span>
                <span className="backtest-run-meta">
                  {c.status}
                  {c.status === "failed" && c.errorCode
                    ? ` · ${c.errorCode}`
                    : null}
                </span>
              </button>
              <button
                type="button"
                className="danger backtest-run-delete"
                onClick={() => onDelete(c.id)}
                aria-label={`Delete comparison ${c.id}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
