import { describe, expect, it } from "vitest";

import {
  identityFromInput,
  isXtFormSymbol,
  KRAKEN_STARTER_IDENTITY,
} from "../services/productIdentity";

describe("product identity", () => {
  it("defaults empty input to Kraken BTC/EUR", () => {
    expect(identityFromInput({})).toEqual(KRAKEN_STARTER_IDENTITY);
  });

  it("infers XT from underscore symbols", () => {
    expect(isXtFormSymbol("btc_usdt")).toBe(true);
    const ident = identityFromInput({ symbol: "btc_usdt" });
    expect(ident.venue).toBe("xt");
    expect(ident.venueProductId).toBe("btc_usdt");
    expect(ident.symbol).toBe("btc_usdt");
  });

  it("keeps Kraken canonical fields for BTC/EUR", () => {
    const ident = identityFromInput({ symbol: "BTC/EUR" });
    expect(ident.venue).toBe("kraken");
    expect(ident.canonicalSymbol).toBe("BTC/EUR");
    expect(ident.venueProductId).toBe("XXBTZEUR");
  });
});
