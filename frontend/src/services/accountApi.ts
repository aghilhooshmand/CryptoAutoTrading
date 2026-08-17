/** Typed client for Feature 013 `/account` (read-only; no credentials). */

export interface VenueBalance {
  asset: string;
  free: string;
  locked: string | null;
  total: string | null;
  venue: string;
}

export interface VenueOrder {
  venueOrderId: string;
  venueProductId: string;
  side: string;
  orderType: string | null;
  quantity: string | null;
  price: string | null;
  executedQty: string | null;
  status: string;
  updatedAt: string | null;
  venue: string;
}

export interface AccountBalancesResponse {
  venue: string;
  retrievedAt: string;
  balances: VenueBalance[];
}

export interface AccountOpenOrdersResponse {
  venue: string;
  retrievedAt: string;
  orders: VenueOrder[];
}

export interface AccountOrderStatusResponse {
  venue: string;
  retrievedAt: string;
  order: VenueOrder;
}

export interface AccountApiError {
  code: string;
  message: string;
}

function accountError(code: string, message: string): AccountApiError {
  return { code, message };
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw accountError(
        "http_error",
        response.ok
          ? "Account response was not valid JSON."
          : `Account request failed (${response.status}). Is the API running and Vite proxying /account?`,
      );
    }
  }
  if (!response.ok) {
    const err = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw accountError(
      err?.code ?? "http_error",
      err?.message ?? (response.statusText || `HTTP ${response.status}`),
    );
  }
  return body as T;
}

export async function fetchAccountBalances(): Promise<AccountBalancesResponse> {
  const response = await fetch("/account/balances");
  return parseJson<AccountBalancesResponse>(response);
}

export async function fetchAccountOpenOrders(
  venueProductId?: string,
): Promise<AccountOpenOrdersResponse> {
  const qs = venueProductId
    ? `?venueProductId=${encodeURIComponent(venueProductId)}`
    : "";
  const response = await fetch(`/account/open-orders${qs}`);
  return parseJson<AccountOpenOrdersResponse>(response);
}

export async function fetchAccountOrderStatus(
  venueOrderId: string,
): Promise<AccountOrderStatusResponse> {
  const response = await fetch(
    `/account/orders/${encodeURIComponent(venueOrderId)}`,
  );
  return parseJson<AccountOrderStatusResponse>(response);
}
