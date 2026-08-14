import type { PortfolioHolding } from "../../services/portfolioApi";
import { formatUsdt, formatWeight } from "./capitalDisplay";

const SLICE_COLORS = ["#2563eb", "#0f766e", "#c2410c", "#7c3aed", "#b45309", "#0369a1"];

interface Props {
  holdings: PortfolioHolding[];
}

export function AllocationVisual({ holdings }: Props) {
  const slices = holdings
    .filter((h) => h.marketValue != null && h.weight != null)
    .map((h, index) => ({
      asset: h.asset,
      weight: Number(h.weight),
      color: SLICE_COLORS[index % SLICE_COLORS.length],
    }))
    .filter((s) => Number.isFinite(s.weight) && s.weight > 0);

  const gradient =
    slices.length === 0
      ? "#e5e7eb"
      : (() => {
          let start = 0;
          const parts: string[] = [];
          for (const slice of slices) {
            const end = start + slice.weight * 360;
            parts.push(`${slice.color} ${start}deg ${end}deg`);
            start = end;
          }
          return parts.join(", ");
        })();

  return (
    <div className="allocation-visual" data-testid="allocation-visual">
      <div
        className="allocation-donut"
        style={{ background: `conic-gradient(${gradient})` }}
        aria-hidden="true"
      />
      <ul className="allocation-legend">
        {slices.length === 0 ? (
          <li className="note">No valued holdings to chart.</li>
        ) : (
          slices.map((slice) => (
            <li key={slice.asset}>
              <span className="allocation-swatch" style={{ background: slice.color }} />
              {slice.asset.toUpperCase()} {formatWeight(String(slice.weight))}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

export function holdingPriceLabel(holding: PortfolioHolding): string {
  if (holding.priceStatus === "unavailable" || holding.price == null) {
    return "unavailable";
  }
  const stale = holding.priceStatus === "stale" ? " (stale)" : "";
  return `${holding.price} USDT${stale}`;
}

export function holdingPnlLabel(holding: PortfolioHolding): string {
  if (holding.asset === "usdt") return "—";
  if (holding.unrealizedPnl == null) return "—";
  return formatUsdt(holding.unrealizedPnl);
}
