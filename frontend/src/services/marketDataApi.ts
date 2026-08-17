/** Typed client for Feature 002 `/market` contracts (normalized models only). */

export type CandleInterval = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

export type MarketStatus =
  | "loading"
  | "fresh"
  | "stale"
  | "unavailable"
  | "unsupported"
  | "error";

export interface TradingPair {
  symbol: string;
  displayName: string;
  baseCurrency: string;
  quoteCurrency: string;
  status: string;
  venue?: string;
  venueProductId?: string | null;
  canonicalSymbol?: string | null;
  baseAsset?: string | null;
  quoteAsset?: string | null;
}

export interface PairsResponse {
  source: string;
  retrievedAt: string;
  pairs: TradingPair[];
}

export interface MarketQuote {
  symbol: string;
  lastPrice: string;
  changeAbsolute?: string | null;
  changePercent?: string | null;
  high24h?: string | null;
  low24h?: string | null;
  volumeBase?: string | null;
  volumeQuote?: string | null;
  source: string;
  observedAt: string;
  retrievedAt: string;
  status: MarketStatus;
}

export interface Candlestick {
  openTime: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volumeBase?: string | null;
  volumeQuote?: string | null;
}

export interface CandlestickSeries {
  symbol: string;
  interval: CandleInterval;
  candles: Candlestick[];
  source: string;
  retrievedAt: string;
}

export interface MarketApiError {
  code: string;
  message: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok) {
    const err = (body as { error?: MarketApiError })?.error;
    const error = new Error(err?.message ?? `Request failed (${response.status})`);
    (error as Error & { code?: string; status?: number }).code =
      err?.code ?? "market_data_unavailable";
    (error as Error & { code?: string; status?: number }).status = response.status;
    throw error;
  }
  return body as T;
}

export async function fetchPairs(
  signal?: AbortSignal,
  venue?: string,
): Promise<PairsResponse> {
  const params = new URLSearchParams();
  if (venue) params.set("venue", venue);
  const suffix = params.toString() ? `?${params}` : "";
  const response = await fetch(`/market/pairs${suffix}`, { signal });
  return parseJson<PairsResponse>(response);
}

export async function fetchQuote(
  symbol: string,
  signal?: AbortSignal,
  venue?: string,
): Promise<MarketQuote> {
  const params = new URLSearchParams({ symbol });
  if (venue) params.set("venue", venue);
  const response = await fetch(`/market/quote?${params}`, { signal });
  return parseJson<MarketQuote>(response);
}

export async function fetchCandles(
  symbol: string,
  interval: CandleInterval,
  signal?: AbortSignal,
  venue?: string,
): Promise<CandlestickSeries> {
  const params = new URLSearchParams({ symbol, interval });
  if (venue) params.set("venue", venue);
  const response = await fetch(`/market/candles?${params}`, { signal });
  return parseJson<CandlestickSeries>(response);
}
