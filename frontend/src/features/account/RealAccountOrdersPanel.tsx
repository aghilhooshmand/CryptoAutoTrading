import { useState, type FormEvent } from "react";

import type { AccountApiError, VenueOrder } from "../../services/accountApi";
import { fetchAccountOrderStatus } from "../../services/accountApi";

type Props = {
  orders: VenueOrder[];
  retrievedAt: string | null;
  venue: string;
  loading: boolean;
  onRefresh: () => void;
  onError: (err: AccountApiError) => void;
};

export function RealAccountOrdersPanel({
  orders,
  retrievedAt,
  venue,
  loading,
  onRefresh,
  onError,
}: Props) {
  const [orderId, setOrderId] = useState("");
  const [lookup, setLookup] = useState<VenueOrder | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);

  async function handleLookup(event: FormEvent) {
    event.preventDefault();
    const id = orderId.trim();
    if (!id) return;
    setLookupBusy(true);
    setLookup(null);
    try {
      const data = await fetchAccountOrderStatus(id);
      setLookup(data.order);
    } catch (err) {
      onError(err as AccountApiError);
    } finally {
      setLookupBusy(false);
    }
  }

  return (
    <section className="real-xt-panel" aria-labelledby="real-account-orders-title">
      <div className="real-xt-panel-header">
        <h2 id="real-account-orders-title">Open orders</h2>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="note">
        Read-only inspection. Place and cancel are not available in this product.
      </p>
      {retrievedAt ? (
        <p className="note">
          Retrieved at {retrievedAt} · venue {venue}
        </p>
      ) : null}
      {orders.length === 0 && !loading ? (
        <p className="note" data-testid="real-account-orders-empty">
          No open orders.
        </p>
      ) : (
        <div className="table-wrap">
          <table data-testid="real-account-orders-table">
            <thead>
              <tr>
                <th scope="col">Order ID</th>
                <th scope="col">Product</th>
                <th scope="col">Side</th>
                <th scope="col">Qty</th>
                <th scope="col">Price</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((row) => (
                <tr key={row.venueOrderId}>
                  <td>{row.venueOrderId}</td>
                  <td>{row.venueProductId}</td>
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
        <label htmlFor="real-account-order-id">
          Order ID
          <input
            id="real-account-order-id"
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
        <p data-testid="real-account-order-lookup-result">
          {lookup.venueOrderId}: {lookup.status} ({lookup.venueProductId}{" "}
          {lookup.side})
        </p>
      ) : null}
    </section>
  );
}
