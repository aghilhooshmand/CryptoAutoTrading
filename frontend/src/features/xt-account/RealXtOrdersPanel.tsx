import { useState, type FormEvent } from "react";

import type { RealXtOrder, XtAccountApiError } from "../../services/xtAccountApi";
import { fetchXtOrderStatus } from "../../services/xtAccountApi";

type Props = {
  orders: RealXtOrder[];
  retrievedAt: string | null;
  loading: boolean;
  onRefresh: () => void;
  onError: (err: XtAccountApiError) => void;
};

export function RealXtOrdersPanel({
  orders,
  retrievedAt,
  loading,
  onRefresh,
  onError,
}: Props) {
  const [orderId, setOrderId] = useState("");
  const [lookup, setLookup] = useState<RealXtOrder | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);

  async function handleLookup(event: FormEvent) {
    event.preventDefault();
    const id = orderId.trim();
    if (!id) return;
    setLookupBusy(true);
    setLookup(null);
    try {
      const data = await fetchXtOrderStatus(id);
      setLookup(data.order);
    } catch (err) {
      onError(err as XtAccountApiError);
    } finally {
      setLookupBusy(false);
    }
  }

  return (
    <section className="real-xt-panel" aria-labelledby="real-xt-orders-title">
      <div className="real-xt-panel-header">
        <h2 id="real-xt-orders-title">Open orders</h2>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="note">
        Read-only inspection. Place and cancel are not available in this product.
      </p>
      {retrievedAt ? (
        <p className="note">Retrieved at {retrievedAt} · provenance real_xt</p>
      ) : null}
      {orders.length === 0 && !loading ? (
        <p className="note" data-testid="real-xt-orders-empty">
          No open orders.
        </p>
      ) : (
        <div className="table-wrap">
          <table data-testid="real-xt-orders-table">
            <thead>
              <tr>
                <th scope="col">Order ID</th>
                <th scope="col">Symbol</th>
                <th scope="col">Side</th>
                <th scope="col">Qty</th>
                <th scope="col">Price</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((row) => (
                <tr key={row.orderId}>
                  <td>{row.orderId}</td>
                  <td>{row.symbol}</td>
                  <td>{row.side}</td>
                  <td>{row.quantity ?? "—"}</td>
                  <td>{row.price ?? "—"}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="real-xt-lookup" onSubmit={(e) => void handleLookup(e)}>
        <h3>Order status lookup</h3>
        <label htmlFor="real-xt-order-id">
          Order ID
          <input
            id="real-xt-order-id"
            name="orderId"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            autoComplete="off"
          />
        </label>
        <button type="submit" disabled={lookupBusy || !orderId.trim()}>
          {lookupBusy ? "Looking up…" : "Look up"}
        </button>
      </form>
      {lookup ? (
        <p data-testid="real-xt-order-lookup-result">
          {lookup.orderId}: {lookup.status} ({lookup.symbol} {lookup.side})
        </p>
      ) : null}
    </section>
  );
}
