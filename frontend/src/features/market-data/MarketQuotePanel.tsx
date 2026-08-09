import type { MarketQuote } from "../../services/marketDataApi";
import { MarketStatusBadge } from "./MarketStatusBadge";

interface Props {
  quote: MarketQuote | null;
  status: string;
  lastError: string | null;
  onRefresh: () => void;
  refreshing: boolean;
}

function Stat({ label, value }: { label: string; value?: string | null }) {
  if (value == null || value === "") return null;
  return (
    <div className="market-stat">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function MarketQuotePanel({
  quote,
  status,
  lastError,
  onRefresh,
  refreshing,
}: Props) {
  const showValues = quote != null && (status === "fresh" || status === "stale");

  return (
    <section className="market-quote" aria-labelledby="market-quote-title">
      <div className="market-quote__header">
        <h2 id="market-quote-title">Market quote</h2>
        <MarketStatusBadge status={status} />
        <button
          type="button"
          className="market-refresh"
          onClick={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {lastError ? (
        <p className="market-error" role="alert">
          {lastError}
        </p>
      ) : null}

      {showValues && quote ? (
        <>
          <p className="market-price">
            <span className="market-price__label">Last price</span>
            <span className="market-price__value">{quote.lastPrice}</span>
            {status === "stale" ? (
              <span className="market-price__stale-note"> (not current)</span>
            ) : null}
          </p>
          <dl className="market-stats">
            <Stat
              label="Change %"
              value={
                quote.changePercent != null ? `${quote.changePercent}%` : null
              }
            />
            <Stat label="Change" value={quote.changeAbsolute} />
            <Stat label="24h high" value={quote.high24h} />
            <Stat label="24h low" value={quote.low24h} />
            <Stat label="Volume (base)" value={quote.volumeBase} />
            <Stat label="Volume (quote)" value={quote.volumeQuote} />
          </dl>
          <p className="market-meta">
            Source: <strong>{quote.source}</strong>
            {" · "}
            Observed: {quote.observedAt}
            {" · "}
            Retrieved: {quote.retrievedAt}
          </p>
        </>
      ) : status === "loading" ? (
        <p>Loading market data…</p>
      ) : (
        <p>No market quote available.</p>
      )}
    </section>
  );
}
