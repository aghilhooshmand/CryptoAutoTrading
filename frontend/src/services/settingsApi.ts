/** Typed client for Feature 008 `/settings` contracts. */

export type SettingsSource = "saved" | "starters";

export interface OperatorSettings {
  symbol: string;
  timeframe: string;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  feeRate: string;
  slippageRate: string;
  targetNetProfitRate: string | null;
  maxSessionLossRate: string | null;
  maxTrades: number | null;
  strategyId: string;
  strategyParams: Record<string, number | string>;
  updatedAt: string | null;
  source: SettingsSource;
  warning: string | null;
}

export type SettingsWriteBody = Omit<
  OperatorSettings,
  "updatedAt" | "source" | "warning"
>;

export interface SettingsApiError {
  code: string;
  message: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok) {
    const err = body?.detail?.error;
    const error: SettingsApiError = {
      code: err?.code ?? "http_error",
      message: err?.message ?? response.statusText,
    };
    throw error;
  }
  return body as T;
}

export async function getSettings(): Promise<OperatorSettings> {
  const response = await fetch("/settings");
  return parseJson<OperatorSettings>(response);
}

export async function putSettings(body: SettingsWriteBody): Promise<OperatorSettings> {
  const response = await fetch("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<OperatorSettings>(response);
}

export async function resetSettings(): Promise<OperatorSettings> {
  const response = await fetch("/settings/reset", { method: "POST" });
  return parseJson<OperatorSettings>(response);
}
