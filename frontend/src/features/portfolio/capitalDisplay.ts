/** Display helpers for the Feature 009 Simulation Portfolio. */

import type { PortfolioSnapshot } from "../../services/portfolioApi";

export function formatUsdt(amount: string | null | undefined): string {
  if (amount == null || amount === "") return "—";
  return `${amount} USDT`;
}

export function formatWeight(ratio: string | null | undefined): string {
  if (ratio == null || ratio === "") return "—";
  const pct = Number(ratio) * 100;
  if (Number.isNaN(pct)) return "—";
  return `${pct.toFixed(2)}%`;
}

export function formatReturn(ratio: string | null | undefined): string {
  if (ratio == null || ratio === "") return "—";
  return formatWeight(ratio);
}

export function formatProvenance(value: string | undefined): string {
  if (value === "exchange") return "exchange";
  return "simulation";
}

/** Equity is the sum of valued holdings; incomplete books are labeled partial. */
export function portfolioEquityDisplay(snapshot: PortfolioSnapshot): string {
  const amount = formatUsdt(snapshot.equity);
  if (snapshot.equityComplete === false) {
    return `${amount} (partial / known-value)`;
  }
  return amount;
}

/**
 * Allocations reserve quote cash; they must not be added on top of holdings equity.
 */
export function allocationsDoNotAffectEquity(snapshot: PortfolioSnapshot): boolean {
  const reserved = Number(snapshot.reserved);
  const cash = Number(snapshot.cash);
  const equity = Number(snapshot.equity);
  if ([reserved, cash, equity].some((n) => Number.isNaN(n))) return false;
  if (reserved > 0 && equity === cash + reserved) return false;
  const holdings = snapshot.holdings ?? [];
  if (holdings.length === 0) {
    return equity === cash;
  }
  const valued = holdings.reduce((sum, holding) => {
    if (holding.marketValue == null) return sum;
    return sum + Number(holding.marketValue);
  }, 0);
  return Math.abs(equity - valued) < 1e-6;
}
