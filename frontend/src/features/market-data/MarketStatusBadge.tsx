import type { MarketStatus } from "../../services/marketDataApi";

interface Props {
  status: MarketStatus | string;
}

export function MarketStatusBadge({ status }: Props) {
  const label = String(status).toUpperCase();
  const isStale = status === "stale";
  return (
    <span
      className={`market-status market-status--${status}`}
      data-testid="market-status"
      data-status={status}
      aria-label={`Market data status: ${label}`}
    >
      {isStale ? "STALE" : label}
    </span>
  );
}
