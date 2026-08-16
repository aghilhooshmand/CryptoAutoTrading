/** Typed client for Feature 013 `/xt-account` (read-only; no credentials). */

export interface RealXtBalance {
  asset: string;
  free: string;
  locked: string;
  total: string | null;
  provenance: "real_xt";
}

export interface RealXtOrder {
  orderId: string;
  symbol: string;
  side: string;
  orderType: string | null;
  quantity: string | null;
  price: string | null;
  executedQty: string | null;
  status: string;
  updatedAt: string | null;
  provenance: "real_xt";
}

export interface RealXtBalancesResponse {
  bookProvenance: "real_xt";
  retrievedAt: string;
  balances: RealXtBalance[];
}

export interface RealXtOpenOrdersResponse {
  bookProvenance: "real_xt";
  retrievedAt: string;
  orders: RealXtOrder[];
}

export interface RealXtOrderStatusResponse {
  bookProvenance: "real_xt";
  retrievedAt: string;
  order: RealXtOrder;
}

export interface XtAccountApiError {
  code: string;
  message: string;
}

function xtError(code: string, message: string): XtAccountApiError {
  return { code, message };
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw xtError(
        "http_error",
        response.ok
          ? "XT account response was not valid JSON."
          : `XT account request failed (${response.status}). Is the API running and Vite proxying /xt-account?`,
      );
    }
  }
  if (!response.ok) {
    const err = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw xtError(
      err?.code ?? "http_error",
      err?.message ?? (response.statusText || `HTTP ${response.status}`),
    );
  }
  return body as T;
}

export async function fetchXtBalances(): Promise<RealXtBalancesResponse> {
  const response = await fetch("/xt-account/balances");
  return parseJson<RealXtBalancesResponse>(response);
}

export async function fetchXtOpenOrders(
  symbol?: string,
): Promise<RealXtOpenOrdersResponse> {
  const qs = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  const response = await fetch(`/xt-account/open-orders${qs}`);
  return parseJson<RealXtOpenOrdersResponse>(response);
}

export async function fetchXtOrderStatus(
  orderId: string,
): Promise<RealXtOrderStatusResponse> {
  const response = await fetch(`/xt-account/orders/${encodeURIComponent(orderId)}`);
  return parseJson<RealXtOrderStatusResponse>(response);
}
