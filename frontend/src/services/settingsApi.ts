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
  portfolioMaxLossRate: string | null;
  portfolioMaxLossAmount: string | null;
  perSymbolMaxWeight: string | null;
  preferredAllocationId: string | null;
  decisionLogMode: "important_only" | "full_audit";
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

function settingsError(code: string, message: string): SettingsApiError {
  return { code, message };
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw settingsError(
        "http_error",
        response.ok
          ? "Settings response was not valid JSON."
          : `Settings request failed (${response.status}). Is the API running and Vite proxying /settings?`,
      );
    }
  }
  if (!response.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const err = (detail as { error?: { code?: string; message?: string } }).error;
      throw settingsError(
        err?.code ?? "http_error",
        err?.message ?? (response.statusText || "Settings request failed"),
      );
    }
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      throw settingsError("invalid_config", first?.msg ?? "Invalid Settings payload");
    }
    throw settingsError(
      "http_error",
      typeof detail === "string" ? detail : response.statusText || `HTTP ${response.status}`,
    );
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
