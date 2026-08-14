import { FormEvent, useState } from "react";

import { InfoTooltip } from "../shared/InfoTooltip";
import {
  type PortfolioApiError,
  type PortfolioSnapshot,
  putPortfolioFunding,
} from "../../services/portfolioApi";
import { formatUsdt, formatReturn, portfolioEquityDisplay } from "./capitalDisplay";

interface Props {
  snapshot: PortfolioSnapshot;
  onUpdated: (next: PortfolioSnapshot) => void;
}

export function PortfolioCapitalPanel({ snapshot, onUpdated }: Props) {
  const [cashInput, setCashInput] = useState(snapshot.cash);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function onFund(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = await putPortfolioFunding(cashInput.trim());
      onUpdated(next);
      setCashInput(next.cash);
      setStatus("Funding saved.");
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Funding failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portfolio-capital" data-testid="portfolio-capital">
      {snapshot.warning ? (
        <p className="form-error" role="alert" data-testid="portfolio-warning">
          {snapshot.warning}
        </p>
      ) : null}

      <dl className="portfolio-metrics" data-testid="portfolio-metrics">
        <div>
          <dt>
            Equity{" "}
            <InfoTooltip
              label="Equity"
              text="Sum of valued holdings in USDT. If any holding has no usable price, this is a partial / known-value total and is not complete book equity."
              testId="help-equity"
            />
          </dt>
          <dd data-testid="metric-equity">{portfolioEquityDisplay(snapshot)}</dd>
        </div>
        <div>
          <dt>
            Cash{" "}
            <InfoTooltip
              label="Cash"
              text="Quote cash is the USDT holding quantity. Allocations reserve this cash; they do not change other asset quantities."
              testId="help-cash"
            />
          </dt>
          <dd data-testid="metric-cash">{formatUsdt(snapshot.cash)}</dd>
        </div>
        <div>
          <dt>
            Available{" "}
            <InfoTooltip
              label="Available"
              text="Cash minus reserved allocations. Available = cash − reserved."
              testId="help-available"
            />
          </dt>
          <dd data-testid="metric-available">{formatUsdt(snapshot.available)}</dd>
        </div>
        <div>
          <dt>
            Reserved{" "}
            <InfoTooltip
              label="Reserved"
              text="Sum of allocation reservations. Reserved capital is not free to allocate again."
              testId="help-reserved"
            />
          </dt>
          <dd data-testid="metric-reserved">{formatUsdt(snapshot.reserved)}</dd>
        </div>
        <div>
          <dt>
            Deployed{" "}
            <InfoTooltip
              label="Deployed"
              text="Capital currently in open market positions. Always 0 until live binding exists."
              testId="help-deployed"
            />
          </dt>
          <dd data-testid="metric-deployed">{formatUsdt(snapshot.deployed)}</dd>
        </div>
        <div>
          <dt>Realized P&amp;L</dt>
          <dd data-testid="metric-realized">{formatUsdt(snapshot.realizedPnl)}</dd>
        </div>
        <div>
          <dt>Unrealized P&amp;L</dt>
          <dd data-testid="metric-unrealized">{formatUsdt(snapshot.unrealizedPnl)}</dd>
        </div>
        <div>
          <dt>
            Total P&amp;L{" "}
            <InfoTooltip
              label="Total P&L"
              text="Realized plus unrealized P&L when every holding has a defined unrealized figure. Shown as unknown if cost basis or value is missing for any holding."
              testId="help-total-pnl"
            />
          </dt>
          <dd data-testid="metric-total-pnl">{formatUsdt(snapshot.totalPnl)}</dd>
        </div>
        <div>
          <dt>
            Total return{" "}
            <InfoTooltip
              label="Total return"
              text="Total P&L divided by cost basis, only when every holding has a known average cost and a usable value. Otherwise unknown — not invented."
              testId="help-total-return"
            />
          </dt>
          <dd data-testid="metric-total-return">{formatReturn(snapshot.totalReturn)}</dd>
        </div>
      </dl>

      <div className="portfolio-positions" data-testid="portfolio-positions">
        <h3>Positions</h3>
        {snapshot.positions.length === 0 ? (
          <p className="note">No open positions in this portfolio foundation.</p>
        ) : null}
      </div>

      <form className="portfolio-funding" onSubmit={onFund} data-testid="portfolio-funding">
        <h3>Fund portfolio</h3>
        <p className="note">
          Set local quote cash (USDT holding). This does not start Simulation or Backtest
          trading and is not real-money brokerage funding.
        </p>
        <label htmlFor="portfolio-cash">
          Quote cash / USDT
          <input
            id="portfolio-cash"
            name="cash"
            inputMode="decimal"
            value={cashInput}
            onChange={(e) => setCashInput(e.target.value)}
            disabled={busy}
            data-testid="funding-cash-input"
          />
        </label>
        {error ? (
          <p className="form-error" role="alert" data-testid="funding-error">
            {error}
          </p>
        ) : null}
        {status ? (
          <p className="form-status" data-testid="funding-status">
            {status}
          </p>
        ) : null}
        <button type="submit" disabled={busy} data-testid="funding-submit">
          {busy ? "Saving…" : "Save funding"}
        </button>
      </form>
    </div>
  );
}
