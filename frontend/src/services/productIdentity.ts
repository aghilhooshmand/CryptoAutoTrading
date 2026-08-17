/** Venue-neutral product identity for Sim/Backtest/Comparison/Settings creates. */

export interface ProductIdentityFields {
  venue: string;
  baseAsset: string;
  quoteAsset: string;
  canonicalSymbol: string;
  venueProductId: string;
  symbol: string;
}

export const KRAKEN_STARTER_IDENTITY: ProductIdentityFields = {
  venue: "kraken",
  baseAsset: "BTC",
  quoteAsset: "EUR",
  canonicalSymbol: "BTC/EUR",
  venueProductId: "XXBTZEUR",
  symbol: "BTC/EUR",
};

export function isXtFormSymbol(raw: string): boolean {
  const text = raw.trim().toLowerCase();
  if (!text || text.includes("/") || text.includes("-")) return false;
  const parts = text.split("_");
  return parts.length === 2 && parts.every(Boolean);
}

export function identityFromInput(input: {
  symbol?: string | null;
  venue?: string | null;
  baseAsset?: string | null;
  quoteAsset?: string | null;
  canonicalSymbol?: string | null;
  venueProductId?: string | null;
}): ProductIdentityFields {
  const symbol = (input.symbol || "").trim();
  const venueRaw = (input.venue || "").trim().toLowerCase();
  const probe = (input.venueProductId || symbol || input.canonicalSymbol || "").trim();

  if (venueRaw === "xt" || (!venueRaw && isXtFormSymbol(probe))) {
    const id = (input.venueProductId || symbol).trim().toLowerCase();
    const [baseRaw, quoteRaw] = id.split("_");
    const base = (input.baseAsset || baseRaw || "").toUpperCase();
    const quote = (input.quoteAsset || quoteRaw || "").toUpperCase();
    return {
      venue: "xt",
      baseAsset: base,
      quoteAsset: quote,
      canonicalSymbol: input.canonicalSymbol || `${base}/${quote}`,
      venueProductId: id,
      symbol: id,
    };
  }

  if (!probe && !input.baseAsset && !input.quoteAsset) {
    return { ...KRAKEN_STARTER_IDENTITY };
  }

  let canonical = (input.canonicalSymbol || "").trim();
  if (!canonical && symbol.includes("/")) canonical = symbol;
  if (!canonical && input.baseAsset && input.quoteAsset) {
    canonical = `${input.baseAsset}/${input.quoteAsset}`;
  }
  const [left, right] = canonical.includes("/")
    ? canonical.split("/", 2)
    : [input.baseAsset || "BTC", input.quoteAsset || "EUR"];
  const base = (input.baseAsset || left || "BTC").toUpperCase();
  const quote = (input.quoteAsset || right || "EUR").toUpperCase();
  const productId =
    (input.venueProductId || "").trim() ||
    (base === "BTC" && quote === "EUR" ? "XXBTZEUR" : `${base}${quote}`);
  return {
    venue: venueRaw || "kraken",
    baseAsset: base,
    quoteAsset: quote,
    canonicalSymbol: `${base}/${quote}`,
    venueProductId: productId,
    symbol: `${base}/${quote}`,
  };
}
