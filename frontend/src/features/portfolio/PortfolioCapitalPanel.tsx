import { FormEvent, useState } from "react";

import { InfoTooltip } from "../shared/InfoTooltip";
import {
  type PortfolioApiError,
  type PortfolioSnapshot,
  putPortfolioFunding,
} from "../../services/portfolioApi";
import { formatUsdt, formatReturn, portfolioEquityDisplay } from "./capitalDisplay";
import { AllocationVisual } from "./AllocationVisual";

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

      <h2>Portfolio summary</h2>
      <dl className="portfolio-metrics" data-testid="portfolio-metrics">
        <div>
          <dt>
            Total value{" "}
            <InfoTooltip
              label="Total value"
              text="Sum of valued holdings in USDT. If any holding has no usable price, this is a partial / known-value total."
              testId="help-equity"
            />
          </dt>
          <dd data-testid="metric-equity">{portfolioEquityDisplay(snapshot)}</dd>
        </div>
        <div>
          <dt>
            Available USDT{" "}
            <InfoTooltip
              label="Available USDT"
              text="Simulation USDT minus reserved allocations. Available = cash − reserved."
              testId="help-available"
            />
          </dt>
          <dd data-testid="metric-available">{formatUsdt(snapshot.available)}</dd>
        </div>
        <div>
          <dt>
            Total P&amp;L{" "}
            <InfoTooltip
              label="Total P&L"
              text="Realized plus unrealized P&L when non-USDT holdings have defined unrealized figures. USDT has no artificial unrealized P&L."
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
              text="Total P&L divided by cost basis when cost and value are known. Otherwise unknown."
              testId="help-total-return"
            />
          </dt>
          <dd data-testid="metric-total-return">{formatReturn(snapshot.totalReturn)}</dd>
        </div>
        <div>
          <dt>Realized P&amp;L</dt>
          <dd data-testid="metric-realized">{formatUsdt(snapshot.realizedPnl)}</dd>
        </div>
        <div>
          <dt>Unrealized P&amp;L</dt>
          <dd data-testid="metric-unrealized">{formatUsdt(snapshot.unrealizedPnl)}</dd>
        </div>
      </dl>

      <h2>Asset allocation</h2>
      <AllocationVisual holdings={snapshot.holdings} />

      <div className="portfolio-compact-capital" data-testid="portfolio-compact-capital">
        <h2>Capital</h2>
        <dl className="portfolio-metrics portfolio-metrics--compact">
          <div>
            <dt>
              USDT cash{" "}
              <InfoTooltip
                label="USDT cash"
                text="Simulation quote cash. This is the USDT holding quantity."
                testId="help-cash"
              />
            </dt>
            <dd data-testid="metric-cash">{formatUsdt(snapshot.cash)}</dd>
          </div>
          <div>
            <dt>Available</dt>
            <dd>{formatUsdt(snapshot.available)}</dd>
          </div>
          <div>
            <dt>
              Reserved{" "}
              <InfoTooltip
                label="Reserved"
                text="Sum of allocation reservations."
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
                text="USDT cost basis of open Simulation positions. Not subtracted again from available."
                testId="help-deployed"
              />
            </dt>
            <dd data-testid="metric-deployed">{formatUsdt(snapshot.deployed)}</dd>
          </div>
        </dl>
      </div>

      <div className="portfolio-positions" data-testid="portfolio-positions">
        {snapshot.positions.length === 0 ? (
          <p className="note">No open simulation positions.</p>
        ) : (
          <ul>
            {snapshot.positions.map((pos) => (
              <li key={pos.sessionId}>
                {pos.asset.toUpperCase()} {pos.side} {pos.quantity}
              </li>
            ))}
          </ul>
        )}
      </div>

      <form className="portfolio-funding" onSubmit={onFund} data-testid="portfolio-funding">
        <h3>Fund simulation USDT</h3>
        <label htmlFor="portfolio-cash">
          Simulation USDT
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
