import type { BacktestDecision } from "../../services/backtestApi";

interface Props {
  decisions: BacktestDecision[];
}

export function BacktestDecisions({ decisions }: Props) {
  return (
    <section className="backtest-decisions" aria-labelledby="backtest-decisions-title">
      <h3 id="backtest-decisions-title">Backtest decisions</h3>
      {decisions.length === 0 ? (
        <p>No decisions.</p>
      ) : (
        <ul>
          {decisions.map((d) => (
            <li key={d.id}>
              {d.signal} → {d.outcome}
              {d.reasonCode ? ` (${d.reasonCode})` : ""}
              {d.candleOpenTime != null ? ` @ ${d.candleOpenTime}` : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
