/** Display helpers for portfolio capital (Feature 009). Equity is cash-only; do not sum allocations. */

import type { PortfolioSnapshot } from "../../services/portfolioApi";

export function formatUsdt(amount: string): string {
  return `${amount} USDT`;
}

/** Portfolio equity must come from snapshot.equity (flat cash), never allocation sums. */
export function portfolioEquityDisplay(snapshot: PortfolioSnapshot): string {
  return formatUsdt(snapshot.equity);
}

export function allocationsDoNotAffectEquity(snapshot: PortfolioSnapshot): boolean {
  const reserved = Number(snapshot.reserved);
  const cash = Number(snapshot.cash);
  const equity = Number(snapshot.equity);
  // v1: equity === cash; reserved is not added into equity
  return equity === cash && !Number.isNaN(reserved);
}
