/**
 * Trading cost defaults and money ↔ rate conversion helpers.
 *
 * Fee default matches XT Spot VIP0 base maker/taker (0.20%).
 * Slippage is a model estimate for adverse fills — XT does not publish a fixed slippage schedule.
 *
 * Absolute USDT amounts convert against max position size (per-trade notional proxy).
 */

export const XT_SPOT_FEE_RATE = "0.002"; // 0.20% VIP0 spot
export const DEFAULT_SLIPPAGE_RATE = "0.0005"; // 0.05% adverse-fill model

export const XT_SPOT_FEE_LABEL = "XT Spot VIP0 0.20%";

function stripTrailingZeros(value: string): string {
  if (!value.includes(".")) return value;
  return value.replace(/\.?0+$/, "") || "0";
}

export function rateToUsdtAmount(
  rate: string,
  notional: string,
): string | null {
  const r = Number(rate);
  const n = Number(notional);
  if (!Number.isFinite(r) || !Number.isFinite(n) || n <= 0 || r < 0) return null;
  return stripTrailingZeros((r * n).toFixed(8));
}

export function usdtAmountToRate(
  amount: string,
  notional: string,
): string | null {
  const a = Number(amount);
  const n = Number(notional);
  if (!Number.isFinite(a) || !Number.isFinite(n) || n <= 0 || a < 0) return null;
  return stripTrailingZeros((a / n).toFixed(8));
}

/** Fraction 0.002 → "0.20%" */
export function rateToPercentPointsLabel(rate: string): string {
  const r = Number(rate);
  if (!Number.isFinite(r)) return "—";
  return `${(r * 100).toFixed(2)}%`;
}
