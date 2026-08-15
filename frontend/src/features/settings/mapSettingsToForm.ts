/** Map Operator Settings → create-form initial values (Feature 008). */

import type { OperatorSettings } from "../../services/settingsApi";
import { COST_DEFAULTS } from "../shared/CostRateFields";
import type { StrategyConfigValue } from "../strategy/StrategyConfigFields";
import { defaultStrategyConfig } from "../strategy/StrategyConfigFields";
import { defaultParamsFor, FALLBACK_STRATEGIES } from "../../services/strategiesApi";

export interface SharedFormSeed {
  symbol: string;
  timeframe: string;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  feeRate: string;
  slippageRate: string;
  /** Empty string when unset in Settings */
  targetNetProfitRate: string;
  maxSessionLossRate: string;
  maxTrades: string;
  portfolioMaxLossRate: string;
  portfolioMaxLossAmount: string;
  perSymbolMaxWeight: string;
  preferredAllocationId: string;
  decisionLogMode: "important_only" | "full_audit";
  strategy: StrategyConfigValue;
}

export function optionalRateToInput(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  return String(value);
}

export function optionalMaxTradesToInput(value: number | null | undefined): string {
  if (value == null) return "";
  return String(value);
}

export function settingsToSharedSeed(settings: OperatorSettings): SharedFormSeed {
  return {
    symbol: settings.symbol || "btc_usdt",
    timeframe: settings.timeframe || "1h",
    startingCapital: settings.startingCapital || "1000",
    allocatedCapital: settings.allocatedCapital || settings.startingCapital || "1000",
    maxPositionSize: settings.maxPositionSize || "1000",
    feeRate: settings.feeRate || COST_DEFAULTS.feeRate,
    slippageRate: settings.slippageRate || COST_DEFAULTS.slippageRate,
    targetNetProfitRate: optionalRateToInput(settings.targetNetProfitRate),
    maxSessionLossRate: optionalRateToInput(settings.maxSessionLossRate),
    maxTrades: optionalMaxTradesToInput(settings.maxTrades),
    portfolioMaxLossRate: optionalRateToInput(settings.portfolioMaxLossRate),
    portfolioMaxLossAmount: optionalRateToInput(settings.portfolioMaxLossAmount),
    perSymbolMaxWeight: optionalRateToInput(settings.perSymbolMaxWeight),
    preferredAllocationId: settings.preferredAllocationId ?? "",
    decisionLogMode: settings.decisionLogMode === "full_audit" ? "full_audit" : "important_only",
    strategy: {
      strategyId: settings.strategyId || "dual_ema",
      strategyParams: { ...(settings.strategyParams || defaultStrategyConfig().strategyParams) },
    },
  };
}

/** Product/registry starter for comparison legs after the first. */
export function comparisonSecondaryLegStarter(): StrategyConfigValue {
  const rsiInfo = FALLBACK_STRATEGIES.find((s) => s.id === "rsi");
  if (rsiInfo) {
    return { strategyId: "rsi", strategyParams: defaultParamsFor(rsiInfo) };
  }
  return defaultStrategyConfig();
}
