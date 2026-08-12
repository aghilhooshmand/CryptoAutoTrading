/** Typed client for Feature 004 `/backtest` contracts. */

export type CandleInterval = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

export interface BacktestSummary {
  startingCapital?: string;
  endingCapital?: string;
  netPnl?: string;
  returnPct?: string;
  tradeCount?: number;
  roundTripCount?: number;
  winningTrades?: number;
  losingTrades?: number;
  winRate?: string;
  totalFees?: string;
  totalSlippage?: string;
  maxDrawdown?: string;
  maxDrawdownPct?: string;
  bestTrade?: string | null;
  worstTrade?: string | null;
  buyAndHoldNetPnl?: string;
  buyAndHoldReturnPct?: string;
  strategyFillCount?: number;
}

export interface BacktestRun {
  id: string;
  status: string;
  symbol: string;
  timeframe: string;
  startTime: number;
  endTime: number;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  targetNetProfitRate: string | null;
  maxSessionLossRate: string | null;
  targetNetProfitAmount: string | null;
  maxSessionLossAmount: string | null;
  maxTrades: number | null;
  feeRate: string;
  slippageRate: string;
  strategyId: string;
  strategyParams?: Record<string, number | string>;
  origin?: "manual" | "comparison";
  comparisonId?: string | null;
  candleCount: number | null;
  createdAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  summary: BacktestSummary | null;
}

export interface CreateBacktestRequest {
  symbol: string;
  timeframe: CandleInterval;
  startTime: number;
  endTime: number;
  startingCapital: string;
  allocatedCapital?: string;
  maxPositionSize: string;
  targetNetProfitRate?: string;
  maxSessionLossRate?: string;
  maxTrades?: number;
  feeRate?: string;
  slippageRate?: string;
  strategyId: string;
  strategyParams?: Record<string, number | string>;
}

export interface BacktestTrade {
  id: string;
  side: string;
  qty: string;
  referencePrice: string;
  fillPrice: string;
  fee: string;
  slippageCost: string;
  notional: string;
  signalCandleOpenTime: number | null;
  fillCandleOpenTime: number;
  isEndOfRunFlatten: boolean;
  isForcedClose: boolean;
}

export interface BacktestDecision {
  id: string;
  candleOpenTime: number | null;
  signal: string;
  outcome: string;
  reasonCode: string | null;
  reasonMessage: string | null;
  fastEma: string | null;
  slowEma: string | null;
}

export interface BacktestApiError {
  code: string;
  message: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const body = await response.json();
  if (!response.ok) {
    const nested =
      (body as { detail?: { error?: BacktestApiError } })?.detail?.error ??
      (body as { error?: BacktestApiError })?.error;
    const error = new Error(nested?.message ?? `Request failed (${response.status})`);
    (error as Error & { code?: string; status?: number }).code =
      nested?.code ?? "backtest_error";
    (error as Error & { code?: string; status?: number }).status = response.status;
    throw error;
  }
  return body as T;
}

export function validateCapitalNesting(
  starting: string,
  allocated: string,
  maxPos: string,
): string | null {
  const s = Number(starting);
  const a = Number(allocated);
  const m = Number(maxPos);
  if (!(m > 0 && m <= a && a <= s)) {
    return "Require 0 < maxPositionSize ≤ allocatedCapital ≤ startingCapital";
  }
  return null;
}

/**
 * Format API rate fractions (0.01 = 1%) for display.
 * Backend stores returnPct / maxDrawdownPct / winRate / buyAndHoldReturnPct as decimals.
 */
export function formatRateAsPercent(
  value: string | number | null | undefined,
  options?: { signed?: boolean; digits?: number },
): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  const digits = options?.digits ?? 2;
  const pct = n * 100;
  if (options?.signed) {
    const sign = pct > 0 ? "+" : pct < 0 ? "-" : "";
    return `${sign}${Math.abs(pct).toFixed(digits)}%`;
  }
  return `${pct.toFixed(digits)}%`;
}

/** Format quote-currency amounts (`$0.26`, or signed `+$1.19` / `-$0.63`). */
export function formatMoneyUsd(
  value: string | number | null | undefined,
  options?: { digits?: number; signed?: boolean },
): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  const digits = options?.digits ?? 2;
  const signed = options?.signed ?? true;
  if (!signed) {
    return `$${Math.abs(n).toFixed(digits)}`;
  }
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toFixed(digits)}`;
}

/** Matches backend `MAX_BACKTEST_CANDLES` (Feature 004 hard cap). */
export const MAX_BACKTEST_CANDLES = 5000;

const INTERVAL_MS: Record<CandleInterval, number> = {
  "1m": 60_000,
  "5m": 5 * 60_000,
  "15m": 15 * 60_000,
  "1h": 60 * 60_000,
  "4h": 4 * 60 * 60_000,
  "1d": 24 * 60 * 60_000,
};

export function estimateCandleCount(
  startMs: number,
  endMs: number,
  interval: CandleInterval,
): number {
  if (!(endMs > startMs)) return 0;
  return Math.max(0, Math.floor((endMs - startMs) / INTERVAL_MS[interval]));
}

/** Human-friendly max window length at the selected timeframe for the 5000-candle cap. */
export function maxWindowHint(interval: CandleInterval): string {
  const ms = INTERVAL_MS[interval] * MAX_BACKTEST_CANDLES;
  const minutes = ms / 60_000;
  if (minutes < 60 * 48) {
    const days = minutes / (60 * 24);
    return `about ${days.toFixed(1)} days`;
  }
  const days = minutes / (60 * 24);
  if (days < 60) return `about ${Math.floor(days)} days`;
  return `about ${Math.floor(days / 30)} months`;
}

export function oversizedHistoryMessage(
  estimated: number,
  interval: CandleInterval,
): string {
  return (
    `Estimated ${estimated.toLocaleString()} candles (max ${MAX_BACKTEST_CANDLES}). ` +
    `At ${interval}, use at most ${maxWindowHint(interval)}, or pick a higher timeframe.`
  );
}

export async function createBacktestRun(
  body: CreateBacktestRequest,
  signal?: AbortSignal,
): Promise<BacktestRun> {
  const response = await fetch("/backtest/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  return parseJson<BacktestRun>(response);
}

export async function listBacktestRuns(
  limit = 20,
  signal?: AbortSignal,
  options?: { includeComparisonOrigin?: boolean },
): Promise<{ runs: BacktestRun[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (options?.includeComparisonOrigin) {
    params.set("includeComparisonOrigin", "true");
  }
  const response = await fetch(`/backtest/runs?${params.toString()}`, { signal });
  return parseJson(response);
}

export async function getBacktestRun(
  id: string,
  signal?: AbortSignal,
): Promise<BacktestRun> {
  const response = await fetch(`/backtest/runs/${id}`, { signal });
  return parseJson(response);
}

export async function getBacktestTrades(
  id: string,
  signal?: AbortSignal,
): Promise<{ trades: BacktestTrade[] }> {
  const response = await fetch(`/backtest/runs/${id}/trades`, { signal });
  return parseJson(response);
}

export async function getBacktestDecisions(
  id: string,
  signal?: AbortSignal,
): Promise<{ decisions: BacktestDecision[] }> {
  const response = await fetch(`/backtest/runs/${id}/decisions`, { signal });
  return parseJson(response);
}

export async function deleteBacktestRun(
  id: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`/backtest/runs/${id}`, {
    method: "DELETE",
    signal,
  });
  await parseJson(response);
}
