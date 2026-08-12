import {
  formatMoneyUsd,
  formatRateAsPercent,
} from "../../services/backtestApi";
import type { StrategyComparison } from "../../services/comparisonApi";

interface Props {
  comparison: StrategyComparison | null;
  onInspectLeg?: (backtestRunId: string) => void;
}

export function ComparisonResultsTable({ comparison, onInspectLeg }: Props) {
  if (!comparison) {
    return (
      <section className="comparison-results" aria-labelledby="comparison-results-title">
        <h3 id="comparison-results-title">Comparison results</h3>
        <p className="hint">Run a comparison to see side-by-side metrics.</p>
      </section>
    );
  }

  if (comparison.status === "failed") {
    return (
      <section className="comparison-results" aria-labelledby="comparison-results-title">
        <h3 id="comparison-results-title">Comparison results</h3>
        <p className="form-error" role="alert">
          {comparison.errorCode}: {comparison.errorMessage}
        </p>
      </section>
    );
  }

  return (
    <section className="comparison-results" aria-labelledby="comparison-results-title">
      <h3 id="comparison-results-title">Comparison results</h3>
      <p className="hint">
        Shared buy-and-hold:{" "}
        {formatRateAsPercent(comparison.buyAndHoldReturnPct, { signed: true })} (
        {formatMoneyUsd(comparison.buyAndHoldNetPnl)}) · {comparison.candleCount ?? "—"}{" "}
        candles. Metrics are shown without an automatic winner.
      </p>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">Strategy</th>
              <th scope="col">Net P&amp;L</th>
              <th scope="col">Return</th>
              <th scope="col">Max DD</th>
              <th scope="col">Win rate</th>
              <th scope="col">Round trips</th>
              <th scope="col">Fills</th>
              <th scope="col">Fees</th>
              <th scope="col">Slippage</th>
              <th scope="col">Best</th>
              <th scope="col">Worst</th>
              <th scope="col">vs B&amp;H</th>
              <th scope="col">Inspect</th>
            </tr>
          </thead>
          <tbody>
            {comparison.legs.map((leg) => (
              <tr key={`${leg.ordinal}-${leg.strategyId}`}>
                <td>
                  {leg.strategyId}
                  <span className="hint"> · leg {leg.ordinal + 1}</span>
                </td>
                <td>{formatMoneyUsd(leg.netPnl)}</td>
                <td>{formatRateAsPercent(leg.returnPct, { signed: true })}</td>
                <td>{formatRateAsPercent(leg.maxDrawdownPct, { signed: true })}</td>
                <td>{formatRateAsPercent(leg.winRate)}</td>
                <td>{leg.roundTripCount ?? "—"}</td>
                <td>{leg.fillCount ?? "—"}</td>
                <td>{formatMoneyUsd(leg.totalFees, { signed: false })}</td>
                <td>{formatMoneyUsd(leg.totalSlippage, { signed: false })}</td>
                <td>{formatMoneyUsd(leg.bestTrade)}</td>
                <td>{formatMoneyUsd(leg.worstTrade)}</td>
                <td>
                  {formatRateAsPercent(leg.vsBuyAndHoldReturnPct, { signed: true })}
                </td>
                <td>
                  {leg.backtestRunId && onInspectLeg ? (
                    <button
                      type="button"
                      onClick={() => onInspectLeg(leg.backtestRunId!)}
                    >
                      Open backtest
                    </button>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
