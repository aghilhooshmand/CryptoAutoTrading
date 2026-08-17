/** Typed client for Feature 003 `/simulation` contracts. */

export type SessionState =
  | "CONFIGURED"
  | "RUNNING"
  | "STOPPING"
  | "RECOVERY_BLOCKED"
  | "STOPPED";

export interface SkippedGapSummary {
  fromOpenTime: string | null;
  toOpenTime: string;
  reason: string;
  recordedAt: string;
}

export type CandleInterval = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

export interface SessionEconomics {
  startEquity: string;
  cash: string;
  markEquity: string | null;
  markNetPnl: string | null;
  unrealizedGross: string | null;
  liquidationEquity: string | null;
  grossPnl: string;
  fees: string;
  slippageCost: string;
  netPnl: string | null;
  targetNetProfitRate: string;
  targetNetProfitAmount: string;
  maxSessionLossRate: string;
  maxSessionLossAmount: string;
  markPrice: string | null;
  markSafe: boolean;
}

export interface PendingConfirmation {
  id: string;
  symbol: string;
  side: string;
  proposedNotional: string;
  referencePrice: string;
  status: string;
  createdAt: string;
  expiresAt: string;
}

export interface RealReconcileSummary {
  xtOrderId: string | null;
  submitStatus: string | null;
  reconcileStatus: string | null;
}

export interface SimulationSession {
  id: string;
  mode: string;
  state: SessionState;
  symbol: string;
  timeframe: string;
  strategyId: string;
  strategyParams?: Record<string, number | string>;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  targetNetProfitRate: string;
  maxSessionLossRate: string;
  targetNetProfitAmount: string;
  maxSessionLossAmount: string;
  maxTrades: number;
  durationSeconds: number;
  feeRate: string;
  slippageRate: string;
  allocationId?: string | null;
  portfolioMaxLossRate?: string | null;
  portfolioMaxLossAmount?: string | null;
  perSymbolMaxWeight?: string | null;
  decisionLogMode: "important_only" | "full_audit";
  takeProfitPercent?: string | null;
  stopLossPercent?: string | null;
  entryFillPrice?: string | null;
  takeProfitPrice?: string | null;
  stopLossPrice?: string | null;
  cash: string;
  cashIsLocalBudgetOnly?: boolean;
  startingCapitalIsLocalBudgetOnly?: boolean;
  positionSide: string;
  positionQty: string;
  tradeCount: number;
  strategyFillCount: number;
  startedAt: string | null;
  stoppedAt: string | null;
  stopReason: string | null;
  positionFlattenStatus: string;
  lastProcessedCandleOpenTime: number | null;
  recoveryReason?: string | null;
  recoveryDetail?: string | null;
  lastRecoveryAt?: string | null;
  skippedGap?: SkippedGapSummary | null;
  pendingConfirmation?: PendingConfirmation | null;
  realReconcile?: RealReconcileSummary | null;
  economics: SessionEconomics;
  finalResult?: FinalResult | null;
  label: "SIMULATION" | "REAL";
}

export interface FinalResult {
  complete: boolean;
  frozenAt: string;
  source: "stop" | "recovery" | "backfill";
  startingCapital: string;
  endingEquity: string | null;
  netPnl: string | null;
  returnPct: string | null;
  cash: string;
  fees: string;
  slippageCost: string;
  tradeCount: number;
  strategyFillCount: number;
  positionFlattenStatus: string;
  stopReason: string | null;
  markEquity: string | null;
  markPrice: string | null;
}

export interface FinalResultSummary {
  complete: boolean;
  netPnl: string | null;
  returnPct: string | null;
}

export interface HistoryListItem {
  id: string;
  state: SessionState;
  symbol: string;
  timeframe: string;
  strategyId: string;
  startedAt: string | null;
  stoppedAt: string | null;
  stopReason: string | null;
  createdAt: string | null;
  finalResultSummary: FinalResultSummary | null;
}

export interface SessionListResponse {
  sessions: HistoryListItem[];
  totalCount: number;
  limit: number;
  offset: number;
}

export interface CreateSessionRequest {
  mode?: string;
  symbol: string;
  timeframe: CandleInterval;
  startingCapital: string;
  allocatedCapital?: string;
  maxPositionSize: string;
  targetNetProfitRate: string;
  maxSessionLossRate: string;
  maxTrades: number;
  durationSeconds: number;
  feeRate?: string;
  slippageRate?: string;
  strategyId: string;
  strategyParams?: Record<string, number | string>;
  allocationId?: string | null;
  portfolioMaxLossRate?: string | null;
  portfolioMaxLossAmount?: string | null;
  perSymbolMaxWeight?: string | null;
  decisionLogMode?: "important_only" | "full_audit";
  /** Optional per-position TP as fraction of entry (e.g. "0.02" = +2%). */
  takeProfitPercent?: string | null;
  /** Optional per-position SL as fraction of entry (e.g. "0.01" = −1%). */
  stopLossPercent?: string | null;
}

export interface DecisionItem {
  id: string;
  createdAt: string;
  candleOpenTime: number | null;
  signal: string;
  outcome: string;
  reasonCode: string | null;
  reasonMessage: string | null;
  fastEma: string | null;
  slowEma: string | null;
}

export interface TradeItem {
  id: string;
  createdAt: string;
  symbol: string;
  side: string;
  qty: string;
  referencePrice: string;
  fillPrice: string;
  fee: string;
  slippageCost: string;
  notional: string;
  cashDelta: string;
  isForcedClose: boolean;
  candleOpenTime: number | null;
}

export interface SimulationApiError {
  code: string;
  message: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok) {
    const nested =
      (body as { detail?: { error?: SimulationApiError } })?.detail?.error ??
      (body as { error?: SimulationApiError })?.error;
    const error = new Error(nested?.message ?? `Request failed (${response.status})`);
    (error as Error & { code?: string; status?: number }).code =
      nested?.code ?? "simulation_error";
    (error as Error & { code?: string; status?: number }).status = response.status;
    throw error;
  }
  return body as T;
}

export async function createSession(
  body: CreateSessionRequest,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch("/simulation/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "simulation", ...body }),
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function startSession(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/start`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function stopSession(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/stop`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function emergencyStopSession(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/emergency-stop`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function resumeSession(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/resume`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function confirmEntry(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/confirm-entry`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function declineEntry(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}/decline-entry`, {
    method: "POST",
    signal,
  });
  return parseJson<SimulationSession>(response);
}

export async function fetchActiveSession(
  signal?: AbortSignal,
): Promise<SimulationSession | null> {
  const response = await fetch("/simulation/sessions/active", { signal });
  const data = await parseJson<{ session: SimulationSession | null }>(response);
  return data.session;
}

export async function fetchSession(
  id: string,
  signal?: AbortSignal,
): Promise<SimulationSession> {
  const response = await fetch(`/simulation/sessions/${id}`, { signal });
  return parseJson<SimulationSession>(response);
}

export async function listSessions(
  opts?: { state?: SessionState; limit?: number; offset?: number },
  signal?: AbortSignal,
): Promise<SessionListResponse> {
  const params = new URLSearchParams();
  if (opts?.state) params.set("state", opts.state);
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  const qs = params.toString();
  const response = await fetch(`/simulation/sessions${qs ? `?${qs}` : ""}`, { signal });
  return parseJson<SessionListResponse>(response);
}

export async function deleteSession(id: string, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`/simulation/sessions/${id}`, {
    method: "DELETE",
    signal,
  });
  if (response.status === 204) return;
  await parseJson<unknown>(response);
}

export async function fetchDecisions(
  id: string,
  limit = 100,
  signal?: AbortSignal,
): Promise<DecisionItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/simulation/sessions/${id}/decisions?${params}`, {
    signal,
  });
  const data = await parseJson<{ items: DecisionItem[] }>(response);
  return data.items;
}

export async function fetchTrades(
  id: string,
  limit = 100,
  signal?: AbortSignal,
): Promise<TradeItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/simulation/sessions/${id}/trades?${params}`, {
    signal,
  });
  const data = await parseJson<{ items: TradeItem[] }>(response);
  return data.items;
}

/** Derive absolute USDT amount from allocated capital and fraction rate. */
export function deriveAmount(allocated: string, rate: string): string | null {
  const a = Number(allocated);
  const r = Number(rate);
  if (!Number.isFinite(a) || !Number.isFinite(r) || a <= 0 || r < 0) return null;
  const amount = a * r;
  if (!Number.isFinite(amount)) return null;
  return amount.toFixed(8).replace(/\.?0+$/, "") || "0";
}

export function rateToPercentLabel(rate: string): string {
  const r = Number(rate);
  if (!Number.isFinite(r)) return "—";
  return `${(r * 100).toFixed(2)}%`;
}

export function validateCapitalNesting(
  starting: string,
  allocated: string,
  maxPosition: string,
): string | null {
  const s = Number(starting);
  const a = Number(allocated);
  const m = Number(maxPosition);
  if (![s, a, m].every((n) => Number.isFinite(n))) {
    return "Capital fields must be valid numbers.";
  }
  if (!(m > 0 && m <= a && a <= s)) {
    return "Require 0 < max position size ≤ allocated capital ≤ starting capital.";
  }
  return null;
}
