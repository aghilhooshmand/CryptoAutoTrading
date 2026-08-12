/** Typed client for Feature 007 `/comparisons` contracts. */

export type ComparisonStatus = "running" | "completed" | "failed";

export interface ComparisonLegInput {
  strategyId: string;
  strategyParams?: Record<string, number | string>;
}

export interface CreateComparisonRequest {
  symbol: string;
  timeframe: string;
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
  legs: ComparisonLegInput[];
}

export interface ComparisonLegResult {
  ordinal: number;
  strategyId: string;
  strategyParams: Record<string, number | string>;
  backtestRunId: string | null;
  netPnl?: string | null;
  returnPct?: string | null;
  maxDrawdown?: string | null;
  maxDrawdownPct?: string | null;
  winRate?: string | null;
  roundTripCount?: number | null;
  fillCount?: number | null;
  totalFees?: string | null;
  totalSlippage?: string | null;
  bestTrade?: string | null;
  worstTrade?: string | null;
  buyAndHoldReturnPct?: string | null;
  vsBuyAndHoldReturnPct?: string | null;
}

export interface StrategyComparison {
  id: string;
  status: ComparisonStatus;
  symbol: string;
  timeframe: string;
  startTime: number;
  endTime: number;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  targetNetProfitRate: string | null;
  maxSessionLossRate: string | null;
  maxTrades: number | null;
  feeRate: string;
  slippageRate: string;
  candleCount: number | null;
  buyAndHoldReturnPct: string | null;
  buyAndHoldNetPnl: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string | null;
  completedAt: string | null;
  legs: ComparisonLegResult[];
}

export interface ComparisonApiError {
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
      (body as { detail?: { error?: ComparisonApiError } })?.detail?.error ??
      (body as { error?: ComparisonApiError })?.error;
    const error = new Error(nested?.message ?? `Request failed (${response.status})`);
    (error as Error & { code?: string; status?: number }).code =
      nested?.code ?? "comparison_error";
    (error as Error & { code?: string; status?: number }).status = response.status;
    throw error;
  }
  return body as T;
}

export const MIN_COMPARISON_LEGS = 2;
export const MAX_COMPARISON_LEGS = 5;

export function validateLegCount(n: number): string | null {
  if (n < MIN_COMPARISON_LEGS || n > MAX_COMPARISON_LEGS) {
    return `A comparison requires ${MIN_COMPARISON_LEGS}–${MAX_COMPARISON_LEGS} strategies`;
  }
  return null;
}

export async function createComparison(
  body: CreateComparisonRequest,
  signal?: AbortSignal,
): Promise<StrategyComparison> {
  const response = await fetch("/comparisons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  return parseJson<StrategyComparison>(response);
}

export async function listComparisons(
  limit = 20,
  signal?: AbortSignal,
): Promise<{ comparisons: StrategyComparison[] }> {
  const response = await fetch(`/comparisons?limit=${limit}`, { signal });
  return parseJson(response);
}

export async function getComparison(
  id: string,
  signal?: AbortSignal,
): Promise<StrategyComparison> {
  const response = await fetch(`/comparisons/${id}`, { signal });
  return parseJson(response);
}

export async function deleteComparison(
  id: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`/comparisons/${id}`, {
    method: "DELETE",
    signal,
  });
  await parseJson(response);
}
