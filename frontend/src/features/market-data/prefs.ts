/** Local Dashboard preferences (pair, interval, favorites) — no server/SQL. */

import type { CandleInterval } from "../../services/marketDataApi";

const SYMBOL_KEY = "cat.dashboard.lastSymbol";
const INTERVAL_KEY = "cat.dashboard.lastInterval";
const FAVORITES_KEY = "cat.dashboard.favorites";

export const DEFAULT_INTERVAL: CandleInterval = "1h";
export const ALLOWED_INTERVALS: CandleInterval[] = ["15m", "1h", "4h", "1d"];

function safeStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function loadLastSymbol(): string | null {
  const storage = safeStorage();
  const value = storage?.getItem(SYMBOL_KEY)?.trim().toLowerCase();
  return value || null;
}

export function saveLastSymbol(symbol: string): void {
  safeStorage()?.setItem(SYMBOL_KEY, symbol.trim().toLowerCase());
}

export function loadLastInterval(): CandleInterval {
  const storage = safeStorage();
  const value = storage?.getItem(INTERVAL_KEY);
  if (value && (ALLOWED_INTERVALS as string[]).includes(value)) {
    return value as CandleInterval;
  }
  return DEFAULT_INTERVAL;
}

export function saveLastInterval(interval: CandleInterval): void {
  safeStorage()?.setItem(INTERVAL_KEY, interval);
}

export function loadFavorites(): string[] {
  const storage = safeStorage();
  const raw = storage?.getItem(FAVORITES_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item): item is string => typeof item === "string")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);
  } catch {
    return [];
  }
}

export function saveFavorites(symbols: string[]): void {
  const normalized = [
    ...new Set(symbols.map((s) => s.trim().toLowerCase()).filter(Boolean)),
  ];
  safeStorage()?.setItem(FAVORITES_KEY, JSON.stringify(normalized));
}

export function toggleFavorite(symbol: string, current: string[]): string[] {
  const key = symbol.trim().toLowerCase();
  const next = current.includes(key)
    ? current.filter((s) => s !== key)
    : [...current, key];
  saveFavorites(next);
  return next;
}

export function pickDefaultSymbol(symbols: string[]): string | null {
  if (symbols.includes("btc_usdt")) return "btc_usdt";
  return symbols[0] ?? null;
}

export function resolveInitialSymbol(
  available: string[],
  persisted: string | null,
): string | null {
  if (persisted && available.includes(persisted)) return persisted;
  return pickDefaultSymbol(available);
}
