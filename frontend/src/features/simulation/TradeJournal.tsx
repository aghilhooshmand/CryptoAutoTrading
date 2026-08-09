import type { TradeItem } from "../../services/simulationApi";

interface Props {
  items: TradeItem[];
}

export function TradeJournal({ items }: Props) {
  return (
    <section
      className="simulation-journal"
      data-testid="trade-journal"
      aria-labelledby="trade-journal-title"
    >
      <h2 id="trade-journal-title">Trade journal</h2>
      {items.length === 0 ? (
        <p className="note">No trades yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Fill</th>
                <th>Fee</th>
                <th>Slippage</th>
                <th>Forced</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.createdAt}</td>
                  <td>{item.side}</td>
                  <td>{item.qty}</td>
                  <td>{item.fillPrice}</td>
                  <td>{item.fee}</td>
                  <td>{item.slippageCost}</td>
                  <td>{item.isForcedClose ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
