import type { RealXtBalance } from "../../services/xtAccountApi";

type Props = {
  balances: RealXtBalance[];
  retrievedAt: string | null;
  loading: boolean;
  onRefresh: () => void;
};

export function RealXtBalancesPanel({
  balances,
  retrievedAt,
  loading,
  onRefresh,
}: Props) {
  return (
    <section className="real-xt-panel" aria-labelledby="real-xt-balances-title">
      <div className="real-xt-panel-header">
        <h2 id="real-xt-balances-title">Balances</h2>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {retrievedAt ? (
        <p className="note">Retrieved at {retrievedAt} · provenance real_xt</p>
      ) : null}
      {balances.length === 0 && !loading ? (
        <p className="note" data-testid="real-xt-balances-empty">
          No non-zero balances on this account.
        </p>
      ) : (
        <div className="table-wrap">
          <table data-testid="real-xt-balances-table">
            <thead>
              <tr>
                <th scope="col">Asset</th>
                <th scope="col">Free</th>
                <th scope="col">Locked</th>
                <th scope="col">Total</th>
              </tr>
            </thead>
            <tbody>
              {balances.map((row) => (
                <tr key={row.asset}>
                  <td>{row.asset}</td>
                  <td>{row.free}</td>
                  <td>{row.locked}</td>
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
