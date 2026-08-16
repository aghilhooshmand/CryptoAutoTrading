import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { RealXtBadge } from "../features/xt-account/RealXtBadge";
import { RealXtBalancesPanel } from "../features/xt-account/RealXtBalancesPanel";
import { RealXtOrdersPanel } from "../features/xt-account/RealXtOrdersPanel";
import {
  fetchXtBalances,
  fetchXtOpenOrders,
  type RealXtBalance,
  type RealXtOrder,
  type XtAccountApiError,
} from "../services/xtAccountApi";

export function RealXtAccountPage() {
  const [balances, setBalances] = useState<RealXtBalance[]>([]);
  const [orders, setOrders] = useState<RealXtOrder[]>([]);
  const [balancesAt, setBalancesAt] = useState<string | null>(null);
  const [ordersAt, setOrdersAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<XtAccountApiError | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bal, open] = await Promise.all([fetchXtBalances(), fetchXtOpenOrders()]);
      setBalances(bal.balances);
      setBalancesAt(bal.retrievedAt);
      setOrders(open.orders);
      setOrdersAt(open.retrievedAt);
    } catch (err) {
      setError(err as XtAccountApiError);
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
    <section className="page real-xt-page" aria-labelledby="real-xt-title">
      <div className="portfolio-title-row">
        <h1 id="real-xt-title">Real XT Account</h1>
        <RealXtBadge />
      </div>
      <p className="note">
        Live exchange account data from XT private API. This is <strong>not</strong> the
        Simulation Portfolio. Credentials are configured only via server environment
        variables — never in this UI. No trading actions are available here.
      </p>
      <p>
        <Link to="/portfolio">Back to Simulation Portfolio</Link>
      </p>

      {error ? (
        <p className="form-error" role="alert" data-testid="real-xt-error">
          [{error.code}] {error.message}
        </p>
      ) : null}

      {loading && !balancesAt && !error ? (
        <p className="note" data-testid="real-xt-loading">
          Loading Real XT account…
        </p>
      ) : null}

      <RealXtBalancesPanel
        balances={balances}
        retrievedAt={balancesAt}
        loading={loading}
        onRefresh={() => void load()}
      />
      <RealXtOrdersPanel
        orders={orders}
        retrievedAt={ordersAt}
        loading={loading}
        onRefresh={() => void load()}
        onError={setError}
      />
    </section>
  );
}
