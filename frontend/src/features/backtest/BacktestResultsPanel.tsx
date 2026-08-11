import type { BacktestRun } from "../../services/backtestApi";
import {
  formatMoneyUsd,
  formatRateAsPercent,
} from "../../services/backtestApi";

interface Props {
  run: BacktestRun | null;
}

function MetricRow({
  label,
  value,
  subValue,
}: {
  label: string;
  value: string;
  subValue?: string;
}) {
  return (
    <div className="backtest-metric">
      <dt>{label}</dt>
      <dd>
        <span className="backtest-metric-value">{value}</span>
        {subValue != null ? (
          <span className="backtest-metric-sub">{subValue}</span>
        ) : null}
      </dd>
    </div>
  );
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
  const fees = Number(s?.totalFees ?? NaN);
  const slip = Number(s?.totalSlippage ?? NaN);
  const totalCost =
    Number.isFinite(fees) && Number.isFinite(slip) ? fees + slip : null;
  const strategyRet = s?.returnPct != null ? Number(s.returnPct) : NaN;
  const bhRet =
    s?.buyAndHoldReturnPct != null ? Number(s.buyAndHoldReturnPct) : NaN;
  const diffRet =
    Number.isFinite(strategyRet) && Number.isFinite(bhRet)
      ? strategyRet - bhRet
      : null;

  const fills = s?.strategyFillCount ?? s?.tradeCount;
  const roundTrips = s?.roundTripCount;

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
      <p data-testid="backtest-strategy">
        Strategy: <strong>{run.strategyId}</strong>
        {run.strategyParams
          ? ` (${Object.entries(run.strategyParams)
              .map(([k, v]) => `${k}=${v}`)
              .join(", ")})`
          : null}
      </p>

      {s && (
        <>
          <dl className="backtest-metrics">
            <MetricRow
              label="Return"
              value={formatRateAsPercent(s.returnPct, { signed: true })}
            />
            <MetricRow
              label="Net Profit/Loss"
              value={formatMoneyUsd(s.netPnl)}
            />
            <MetricRow
              label="Win Rate"
              value={formatRateAsPercent(s.winRate)}
            />
            <MetricRow
              label="Max Drawdown"
              value={formatRateAsPercent(
                s.maxDrawdownPct == null
                  ? null
                  : -Math.abs(Number(s.maxDrawdownPct)),
                { signed: true },
              )}
              subValue={formatMoneyUsd(s.maxDrawdown, { signed: false })}
            />
          </dl>

          {(fills != null || roundTrips != null) && (
            <p className="backtest-activity">
              {fills != null ? `${fills} fills` : null}
              {fills != null && roundTrips != null ? (
                <br />
              ) : null}
              {roundTrips != null ? `${roundTrips} round trips` : null}
            </p>
          )}

          <div className="backtest-metrics-block">
            <h4 className="backtest-metrics-heading">Trading Costs</h4>
            <dl className="backtest-metrics">
              <MetricRow
                label="Fees"
                value={formatMoneyUsd(s.totalFees, { signed: false })}
              />
              <MetricRow
                label="Slippage"
                value={formatMoneyUsd(s.totalSlippage, { signed: false })}
              />
              <MetricRow
                label="Total"
                value={formatMoneyUsd(totalCost, { signed: false })}
              />
            </dl>
          </div>

          <dl className="backtest-metrics">
            <MetricRow
              label="Best Trade"
              value={formatMoneyUsd(s.bestTrade)}
            />
            <MetricRow
              label="Worst Trade"
              value={formatMoneyUsd(s.worstTrade)}
            />
          </dl>

          <dl className="backtest-metrics">
            <MetricRow
              label="Strategy"
              value={formatRateAsPercent(s.returnPct, { signed: true })}
            />
            <MetricRow
              label="Buy & Hold"
              value={formatRateAsPercent(s.buyAndHoldReturnPct, {
                signed: true,
              })}
            />
            <MetricRow
              label="Difference"
              value={formatRateAsPercent(diffRet, { signed: true })}
            />
          </dl>
        </>
      )}
    </section>
  );
}
