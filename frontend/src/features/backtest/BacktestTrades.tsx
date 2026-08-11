import type { BacktestTrade } from "../../services/backtestApi";

interface Props {
  trades: BacktestTrade[];
}

export function BacktestTrades({ trades }: Props) {
  return (
    <section className="backtest-trades" aria-labelledby="backtest-trades-title">
      <h3 id="backtest-trades-title">Backtest trades</h3>
      {trades.length === 0 ? (
        <p>No trades.</p>
      ) : (
        <ul>
          {trades.map((t) => (
            <li key={t.id}>
              {t.side} qty={t.qty} ref={t.referencePrice} fill={t.fillPrice} fee={t.fee}
              {t.isEndOfRunFlatten ? " [end-of-run flatten]" : ""}
              {t.isForcedClose && !t.isEndOfRunFlatten ? " [forced]" : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
