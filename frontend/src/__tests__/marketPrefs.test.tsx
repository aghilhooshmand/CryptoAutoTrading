import { beforeEach, describe, expect, it } from "vitest";

import {
  loadFavorites,
  loadLastInterval,
  loadLastSymbol,
  resolveInitialSymbol,
  saveFavorites,
  saveLastInterval,
  saveLastSymbol,
  toggleFavorite,
} from "../features/market-data/prefs";

describe("market prefs", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists last symbol and interval with default 1h", () => {
    expect(loadLastInterval()).toBe("1h");
    saveLastInterval("4h");
    expect(loadLastInterval()).toBe("4h");
    saveLastInterval("1m");
    expect(loadLastInterval()).toBe("1m");
    saveLastInterval("5m");
    expect(loadLastInterval()).toBe("5m");
    saveLastSymbol("eth_usdt");
    expect(loadLastSymbol()).toBe("eth_usdt");
  });

  it("keeps favorites before full list via ordered storage and resolve rules", () => {
    const next = toggleFavorite("eth_usdt", []);
    expect(next).toEqual(["eth_usdt"]);
    expect(loadFavorites()).toEqual(["eth_usdt"]);
    saveFavorites(["eth_usdt", "btc_usdt"]);
    expect(loadFavorites()[0]).toBe("eth_usdt");
  });

  it("falls back when persisted symbol is unsupported", () => {
    expect(resolveInitialSymbol(["btc_usdt", "eth_usdt"], "gone_usdt")).toBe(
      "btc_usdt",
    );
    expect(resolveInitialSymbol(["eth_usdt"], null)).toBe("eth_usdt");
  });
});
