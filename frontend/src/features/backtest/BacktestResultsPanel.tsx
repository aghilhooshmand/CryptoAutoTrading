import type { BacktestRun } from "../../services/backtestApi";

interface Props {
  run: BacktestRun | null;
}

export function BacktestResultsPanel({ run }: Props) {
  if (!run) {
    return (
      <section className="backtest-results" aria-labelledby="backtest-results-title">
        <h3 id="backtest-results-title">Backtest results</h3>
        <p>No run selected yet.</p>
      </section>
    );
  }
  const s = run.summary;
  return (
    <section className="backtest-results" aria-labelledby="backtest-results-title">
      <h3 id="backtest-results-title">Backtest results</h3>
      <p className="hint">
        Historical evaluation only — past Dual EMA results are evidence, not a
        guarantee of future profit.
      </p>
      <p>
        Status: <strong>{run.status}</strong>
        {run.errorCode ? ` (${run.errorCode}: ${run.errorMessage})` : null}
      </p>
      {s && (
        <dl className="backtest-summary-grid">
          <dt>Starting capital</dt>
          <dd>{s.startingCapital}</dd>
          <dt>Ending capital</dt>
          <dd>{s.endingCapital}</dd>
          <dt>Net P&amp;L</dt>
          <dd>{s.netPnl}</dd>
          <dt>Return %</dt>
          <dd>{s.returnPct}</dd>
          <dt>Trades</dt>
          <dd>{s.tradeCount}</dd>
          <dt>Win rate</dt>
          <dd>{s.winRate}</dd>
          <dt>Max drawdown</dt>
          <dd>
            {s.maxDrawdown} ({s.maxDrawdownPct})
          </dd>
          <dt>Fees / slippage</dt>
          <dd>
            {s.totalFees} / {s.totalSlippage}
          </dd>
          <dt>Best / worst</dt>
          <dd>
            {s.bestTrade ?? "—"} / {s.worstTrade ?? "—"}
          </dd>
          <dt>Buy &amp; hold</dt>
          <dd>
            {s.buyAndHoldNetPnl} ({s.buyAndHoldReturnPct})
          </dd>
        </dl>
      )}
    </section>
  );
}
