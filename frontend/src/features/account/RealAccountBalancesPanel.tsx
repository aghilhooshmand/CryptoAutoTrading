import type { VenueBalance } from "../../services/accountApi";

type Props = {
  balances: VenueBalance[];
  retrievedAt: string | null;
  venue: string;
  loading: boolean;
  onRefresh: () => void;
};

export function RealAccountBalancesPanel({
  balances,
  retrievedAt,
  venue,
  loading,
  onRefresh,
}: Props) {
  return (
    <section className="real-xt-panel" aria-labelledby="real-account-balances-title">
      <div className="real-xt-panel-header">
        <h2 id="real-account-balances-title">Balances</h2>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {retrievedAt ? (
        <p className="note">
          Retrieved at {retrievedAt} · venue {venue}
        </p>
      ) : null}
      {balances.length === 0 && !loading ? (
        <p className="note" data-testid="real-account-balances-empty">
          No non-zero balances on this account.
        </p>
      ) : (
        <div className="table-wrap">
          <table data-testid="real-account-balances-table">
            <thead>
              <tr>
                <th scope="col">Asset</th>
                <th scope="col">Available</th>
                <th scope="col">Held</th>
                <th scope="col">Total</th>
              </tr>
            </thead>
            <tbody>
              {balances.map((row) => (
                <tr key={`${row.venue}-${row.asset}`}>
                  <td>{row.asset}</td>
                  <td>{row.free}</td>
                  <td>{row.locked ?? "—"}</td>
                  <td>{row.total ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
