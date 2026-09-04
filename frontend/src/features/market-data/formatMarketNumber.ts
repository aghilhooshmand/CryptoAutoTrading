/** Display helpers for market quote amounts (UI only; do not invent prices). */

function stripTrailingZeros(text: string): string {
  if (!text.includes(".")) return text;
  return text.replace(/\.?0+$/, "") || "0";
}

/**
 * Format a decimal string for Dashboard quote stats.
 * Caps fractional digits so long API residues do not smash adjacent cells.
 */
export function formatMarketAmount(
  value: string | null | undefined,
  maxFractionDigits = 8,
): string | null {
  if (value == null || value === "") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(trimmed)) return trimmed;
  const negative = trimmed.startsWith("-");
  const abs = negative ? trimmed.slice(1) : trimmed;
  const [intPart, fracPart = ""] = abs.split(".");
  const cappedFrac = fracPart.slice(0, Math.max(0, maxFractionDigits));
  const joined = cappedFrac.length > 0 ? `${intPart}.${cappedFrac}` : intPart;
  const normalized = stripTrailingZeros(joined);
  return negative && normalized !== "0" ? `-${normalized}` : normalized;
}

export function formatMarketPercent(
  value: string | null | undefined,
): string | null {
  const amount = formatMarketAmount(value, 2);
  return amount == null ? null : `${amount}%`;
}
