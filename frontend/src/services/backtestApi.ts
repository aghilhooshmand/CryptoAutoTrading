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
): Promise<{ runs: BacktestRun[] }> {
  const response = await fetch(`/backtest/runs?limit=${limit}`, { signal });
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
