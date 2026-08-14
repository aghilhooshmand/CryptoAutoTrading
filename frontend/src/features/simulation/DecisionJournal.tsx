import type { DecisionItem } from "../../services/simulationApi";

interface Props {
  items: DecisionItem[];
}

export function DecisionJournal({ items }: Props) {
  return (
    <section
      className="simulation-journal"
      data-testid="decision-journal"
      aria-labelledby="decision-journal-title"
    >
      <h2 id="decision-journal-title">Decision journal</h2>
      {items.length === 0 ? (
        <p className="note">No decisions yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Signal</th>
                <th>Outcome</th>
                <th>Reason</th>
                <th>EMA 9/21</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.createdAt}</td>
                  <td>{item.signal}</td>
                  <td>{item.outcome}</td>
                  <td>
                    {item.reasonCode || item.reasonMessage
                      ? [item.reasonCode, item.reasonMessage].filter(Boolean).join(" — ")
                      : "—"}
                  </td>
                  <td>
                    {item.fastEma ?? "—"} / {item.slowEma ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
