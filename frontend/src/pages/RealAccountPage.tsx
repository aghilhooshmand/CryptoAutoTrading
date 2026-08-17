import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { RealAccountBadge } from "../features/account/RealAccountBadge";
import { RealAccountBalancesPanel } from "../features/account/RealAccountBalancesPanel";
import { RealAccountOrdersPanel } from "../features/account/RealAccountOrdersPanel";
import {
  fetchAccountBalances,
  fetchAccountOpenOrders,
  type AccountApiError,
  type VenueBalance,
  type VenueOrder,
} from "../services/accountApi";

export function RealAccountPage() {
  const [balances, setBalances] = useState<VenueBalance[]>([]);
  const [orders, setOrders] = useState<VenueOrder[]>([]);
  const [venue, setVenue] = useState("kraken");
  const [balancesAt, setBalancesAt] = useState<string | null>(null);
  const [ordersAt, setOrdersAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AccountApiError | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bal, open] = await Promise.all([
        fetchAccountBalances(),
        fetchAccountOpenOrders(),
      ]);
      setBalances(bal.balances);
      setBalancesAt(bal.retrievedAt);
      setVenue(bal.venue || open.venue || "kraken");
      setOrders(open.orders);
      setOrdersAt(open.retrievedAt);
    } catch (err) {
      setError(err as AccountApiError);
      setBalances([]);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="page real-xt-page" aria-labelledby="real-account-title">
      <div className="portfolio-title-row">
        <h1 id="real-account-title">Real Account</h1>
        <RealAccountBadge />
      </div>
      <p className="note">
        Live exchange account data from Kraken private API. Venue:{" "}
        <strong>Kraken</strong>. This is <strong>not</strong> the Simulation
        Portfolio. Credentials are configured only via server environment
        variables — never in this UI. No trading actions are available here.
      </p>
      <p>
        <Link to="/portfolio">Back to Simulation Portfolio</Link>
      </p>

      {error ? (
        <p className="form-error" role="alert" data-testid="real-account-error">
          [{error.code}] {error.message}
        </p>
      ) : null}

      {loading && !balancesAt && !error ? (
        <p className="note" data-testid="real-account-loading">
          Loading Real Account…
        </p>
      ) : null}

      <RealAccountBalancesPanel
        balances={balances}
        retrievedAt={balancesAt}
        venue={venue}
        loading={loading}
        onRefresh={() => void load()}
      />
      <RealAccountOrdersPanel
        orders={orders}
        retrievedAt={ordersAt}
        venue={venue}
        loading={loading}
        onRefresh={() => void load()}
        onError={setError}
      />
    </section>
  );
}
