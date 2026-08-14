/** Typed client for Feature 009 `/portfolio` contracts. */

export interface PortfolioAllocation {
  id: string;
  label: string;
  reservedSize: string;
  targetRef: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PortfolioHolding {
  id: string;
  asset: string;
  quantity: string;
  averageCost: string | null;
  price: string | null;
  priceStatus: "fresh" | "stale" | "unavailable";
  marketValue: string | null;
  weight: string | null;
  realizedPnl: string;
  unrealizedPnl: string | null;
  return: string | null;
  provenance: string;
  createdAt: string;
  updatedAt: string;
}

export interface PortfolioSnapshot {
  quoteCurrency?: string;
  bookProvenance?: string;
  cash: string;
  reserved: string;
  available: string;
  deployed: string;
  realizedPnl: string;
  unrealizedPnl: string;
  equity: string;
  equityComplete: boolean;
  unvaluedAssets: string[];
  positions: unknown[];
  holdings: PortfolioHolding[];
  allocations: PortfolioAllocation[];
  updatedAt: string | null;
  warning: string | null;
}

export interface PortfolioApiError {
  code: string;
  message: string;
}

function portfolioError(code: string, message: string): PortfolioApiError {
  return { code, message };
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw portfolioError(
        "http_error",
        response.ok
          ? "Portfolio response was not valid JSON."
          : `Portfolio request failed (${response.status}). Is the API running and Vite proxying /portfolio?`,
      );
    }
  }
  if (!response.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const err = (detail as { error?: { code?: string; message?: string } }).error;
      throw portfolioError(
        err?.code ?? "http_error",
        err?.message ?? (response.statusText || "Portfolio request failed"),
      );
    }
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      throw portfolioError("invalid_config", first?.msg ?? "Invalid Portfolio payload");
    }
    throw portfolioError(
      "http_error",
      typeof detail === "string" ? detail : response.statusText || `HTTP ${response.status}`,
    );
  }
  return body as T;
}

export async function getPortfolio(): Promise<PortfolioSnapshot> {
  const response = await fetch("/portfolio");
  return parseJson<PortfolioSnapshot>(response);
}

export async function putPortfolioFunding(cash: string): Promise<PortfolioSnapshot> {
  const response = await fetch("/portfolio/funding", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cash }),
  });
  return parseJson<PortfolioSnapshot>(response);
}

export async function putHolding(body: {
  asset: string;
  quantity: string;
  averageCost?: string | null;
}): Promise<PortfolioSnapshot> {
  const response = await fetch("/portfolio/holdings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      asset: body.asset,
      quantity: body.quantity,
      averageCost: body.averageCost ?? null,
    }),
  });
  return parseJson<PortfolioSnapshot>(response);
}

export async function deleteHolding(asset: string): Promise<PortfolioSnapshot> {
  const response = await fetch(`/portfolio/holdings/${encodeURIComponent(asset)}`, {
    method: "DELETE",
  });
  return parseJson<PortfolioSnapshot>(response);
}

export async function createAllocation(body: {
  label: string;
  reservedSize: string;
  targetRef?: string | null;
}): Promise<PortfolioSnapshot> {
  const response = await fetch("/portfolio/allocations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      label: body.label,
      reservedSize: body.reservedSize,
      targetRef: body.targetRef ?? null,
    }),
  });
  return parseJson<PortfolioSnapshot>(response);
}

export async function resizeAllocation(
  id: string,
  reservedSize: string,
): Promise<PortfolioSnapshot> {
  const response = await fetch(`/portfolio/allocations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reservedSize }),
  });
  return parseJson<PortfolioSnapshot>(response);
}

export async function releaseAllocation(id: string): Promise<PortfolioSnapshot> {
  const response = await fetch(`/portfolio/allocations/${id}`, {
    method: "DELETE",
  });
  return parseJson<PortfolioSnapshot>(response);
}
