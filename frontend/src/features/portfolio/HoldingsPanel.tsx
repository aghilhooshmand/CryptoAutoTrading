import type { PortfolioHolding, PortfolioSnapshot } from "../../services/portfolioApi";
import { formatProvenance, formatUsdt, formatWeight } from "./capitalDisplay";
import {
  holdingAvgCostLabel,
  holdingPriceLabel,
  holdingRealizedLabel,
  holdingReturnLabel,
  holdingUnrealizedLabel,
} from "./AllocationVisual";

interface Props {
  snapshot: PortfolioSnapshot;
}

function HoldingCard({ holding }: { holding: PortfolioHolding }) {
  return (
    <article className="holding-card" data-testid={`holding-card-${holding.asset}`}>
      <h3>{holding.asset.toUpperCase()}</h3>
      <dl>
        <div>
          <dt>Quantity</dt>
          <dd>{holding.quantity}</dd>
        </div>
        <div>
          <dt>Price</dt>
          <dd>{holdingPriceLabel(holding)}</dd>
        </div>
        <div>
          <dt>Value</dt>
          <dd>{formatUsdt(holding.marketValue)}</dd>
        </div>
        <div>
          <dt>Avg cost</dt>
          <dd>{holdingAvgCostLabel(holding)}</dd>
        </div>
        <div>
          <dt>Realized</dt>
          <dd>{holdingRealizedLabel(holding)}</dd>
        </div>
        <div>
          <dt>Unrealized</dt>
          <dd>{holdingUnrealizedLabel(holding)}</dd>
        </div>
        <div>
          <dt>Return</dt>
          <dd>{holdingReturnLabel(holding)}</dd>
        </div>
        <div>
          <dt>Weight</dt>
          <dd>{formatWeight(holding.weight)}</dd>
        </div>
      </dl>
      <p className="note">{formatProvenance(holding.provenance)}</p>
    </article>
  );
}

export function HoldingsPanel({ snapshot }: Props) {
  return (
    <div className="portfolio-holdings" data-testid="portfolio-holdings">
      <h2>Holdings</h2>

      <div className="holdings-table-wrap holdings-table-desktop">
        <table className="holdings-table" data-testid="holdings-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Value</th>
              <th>Avg cost</th>
              <th>Realized</th>
              <th>Unrealized</th>
              <th>Return</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.holdings.length === 0 ? (
              <tr>
                <td colSpan={9} className="note">
                  No holdings yet. Fund simulation USDT to start.
                </td>
              </tr>
            ) : (
              snapshot.holdings.map((holding) => (
                <tr key={holding.id} data-testid={`holding-row-${holding.asset}`}>
                  <td data-testid={`holding-asset-${holding.asset}`}>{holding.asset.toUpperCase()}</td>
                  <td data-testid={`holding-qty-${holding.asset}`}>{holding.quantity}</td>
                  <td data-testid={`holding-price-${holding.asset}`}>{holdingPriceLabel(holding)}</td>
                  <td data-testid={`holding-value-${holding.asset}`}>
                    {formatUsdt(holding.marketValue)}
                  </td>
                  <td data-testid={`holding-avg-${holding.asset}`}>{holdingAvgCostLabel(holding)}</td>
                  <td data-testid={`holding-realized-${holding.asset}`}>
                    {holdingRealizedLabel(holding)}
                  </td>
                  <td data-testid={`holding-unrealized-${holding.asset}`}>
                    {holdingUnrealizedLabel(holding)}
                  </td>
                  <td data-testid={`holding-return-${holding.asset}`}>{holdingReturnLabel(holding)}</td>
                  <td data-testid={`holding-weight-${holding.asset}`}>
                    {formatWeight(holding.weight)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="holdings-cards" data-testid="holdings-cards">
        {snapshot.holdings.length === 0 ? (
          <p className="note">No holdings yet. Fund simulation USDT to start.</p>
        ) : (
          snapshot.holdings.map((holding) => <HoldingCard key={holding.id} holding={holding} />)
        )}
      </div>
    </div>
  );
}
