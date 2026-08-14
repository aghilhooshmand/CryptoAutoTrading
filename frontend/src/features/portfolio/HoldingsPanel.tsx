import { FormEvent, useState } from "react";

import {
  type PortfolioApiError,
  type PortfolioHolding,
  type PortfolioSnapshot,
  deleteHolding,
  putHolding,
} from "../../services/portfolioApi";
import { formatProvenance, formatUsdt, formatWeight } from "./capitalDisplay";

interface Props {
  snapshot: PortfolioSnapshot;
  onUpdated: (next: PortfolioSnapshot) => void;
}

function priceCell(holding: PortfolioHolding): string {
  if (holding.priceStatus === "unavailable" || holding.price == null) {
    return "unavailable";
  }
  const stale = holding.priceStatus === "stale" ? " (stale)" : "";
  return `${holding.price} USDT${stale}`;
}

export function HoldingsPanel({ snapshot, onUpdated }: Props) {
  const [asset, setAsset] = useState("btc");
  const [quantity, setQuantity] = useState("");
  const [averageCost, setAverageCost] = useState("");
  const [busy, setBusy] = useState(false);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function onRecord(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = await putHolding({
        asset: asset.trim().toLowerCase(),
        quantity: quantity.trim(),
        averageCost: averageCost.trim() || null,
      });
      onUpdated(next);
      setQuantity("");
      setAverageCost("");
      setStatus("Holding saved.");
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Could not save holding");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(holding: PortfolioHolding) {
    if (rowBusy) return;
    const ok = window.confirm(
      `Remove ${holding.asset.toUpperCase()} holding (quantity ${holding.quantity})? This does not place an exchange order.`,
    );
    if (!ok) return;
    setRowBusy(holding.asset);
    setError(null);
    setStatus(null);
    try {
      const next = await deleteHolding(holding.asset);
      onUpdated(next);
      setStatus(`Removed ${holding.asset.toUpperCase()}.`);
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Could not remove holding");
    } finally {
      setRowBusy(null);
    }
  }

  return (
    <div className="portfolio-holdings" data-testid="portfolio-holdings">
      <h2>Holdings</h2>
      <p className="note">
        Local/manual balances on this book. Quote cash is the USDT line. This is not a
        live XT account. Prices come from public USDT markets when available.
      </p>

      <div className="holdings-table-wrap">
        <table className="holdings-table" data-testid="holdings-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Value</th>
              <th>Weight</th>
              <th>Avg cost</th>
              <th>Unrealized</th>
              <th>Return</th>
              <th>Provenance</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {snapshot.holdings.length === 0 ? (
              <tr>
                <td colSpan={10} className="note">
                  No holdings yet. Fund USDT or record a local asset.
                </td>
              </tr>
            ) : (
              snapshot.holdings.map((holding) => (
                <tr key={holding.id} data-testid={`holding-row-${holding.asset}`}>
                  <td data-testid={`holding-asset-${holding.asset}`}>{holding.asset.toUpperCase()}</td>
                  <td data-testid={`holding-qty-${holding.asset}`}>{holding.quantity}</td>
                  <td data-testid={`holding-price-${holding.asset}`}>{priceCell(holding)}</td>
                  <td data-testid={`holding-value-${holding.asset}`}>
                    {formatUsdt(holding.marketValue)}
                  </td>
                  <td data-testid={`holding-weight-${holding.asset}`}>
                    {formatWeight(holding.weight)}
                  </td>
                  <td>{holding.averageCost ?? "—"}</td>
                  <td>{holding.unrealizedPnl != null ? formatUsdt(holding.unrealizedPnl) : "—"}</td>
                  <td>{holding.return ?? "—"}</td>
                  <td data-testid={`holding-provenance-${holding.asset}`}>
                    {formatProvenance(holding.provenance)}
                  </td>
                  <td>
                    {holding.asset === "usdt" ? (
                      <span className="note">Use funding</span>
                    ) : (
                      <button
                        type="button"
                        className="danger"
                        disabled={rowBusy === holding.asset}
                        onClick={() => void onDelete(holding)}
                        data-testid={`holding-delete-${holding.asset}`}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <form className="holdings-form" onSubmit={onRecord} data-testid="holdings-form">
        <h3>Record local holding</h3>
        <label htmlFor="holding-asset">
          Asset
          <input
            id="holding-asset"
            value={asset}
            onChange={(e) => setAsset(e.target.value)}
            disabled={busy}
            data-testid="holding-asset-input"
          />
        </label>
        <label htmlFor="holding-qty">
          Quantity
          <input
            id="holding-qty"
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={busy}
            required
            data-testid="holding-qty-input"
          />
        </label>
        <label htmlFor="holding-avg">
          Average cost (USDT, optional)
          <input
            id="holding-avg"
            inputMode="decimal"
            value={averageCost}
            onChange={(e) => setAverageCost(e.target.value)}
            disabled={busy}
            data-testid="holding-avg-input"
          />
        </label>
        {error ? (
          <p className="form-error" role="alert" data-testid="holding-error">
            {error}
          </p>
        ) : null}
        {status ? (
          <p className="form-status" data-testid="holding-status">
            {status}
          </p>
        ) : null}
        <button type="submit" disabled={busy} data-testid="holding-submit">
          {busy ? "Saving…" : "Save holding"}
        </button>
      </form>
    </div>
  );
}
