import type { CandleInterval } from "../../services/simulationApi";
import { COST_DEFAULTS } from "../shared/CostRateFields";

/** Fields a named preset may overwrite (subset of session config). */
export type SessionPresetPatch = {
  mode?: "simulation" | "real";
  timeframe?: CandleInterval;
  startingCapital?: string;
  allocatedCapital?: string;
  maxPositionSize?: string;
  targetNetProfitRate?: string;
  maxSessionLossRate?: string;
  maxTrades?: string;
  durationSeconds?: string;
  feeRate?: string;
  slippageRate?: string;
  allocationId?: string;
  portfolioMaxLossRate?: string;
  portfolioMaxLossAmount?: string;
  perSymbolMaxWeight?: string;
  decisionLogMode?: "important_only" | "full_audit";
  takeProfitPercent?: string;
  stopLossPercent?: string;
};

export type SessionPresetId =
  | "torque_smoke"
  | "quick_paper"
  | "conservative"
  | "custom";

export type SessionPreset = {
  id: SessionPresetId;
  label: string;
  description: string;
  /** When set, applied on select. Custom has no patch. Does not change strategy. */
  patch?: SessionPresetPatch;
};

/**
 * Named Simulation setups. Rates are fractions of allocated capital
 * (0.01 = 1%). Fee/slippage are fill fractions (0.002 = 0.2%).
 */
export const SESSION_PRESETS: SessionPreset[] = [
  {
    id: "torque_smoke",
    label: "1 · Torque smoke test",
    description:
      "Fast check that Torque decisions and fills work. Short 1m candles, full decision log, loose stop goals so the session can run and produce activity. Does not change your strategy choice.",
    patch: {
      mode: "simulation",
      timeframe: "1m",
      startingCapital: "200",
      allocatedCapital: "200",
      maxPositionSize: "100",
      targetNetProfitRate: "0.02",
      maxSessionLossRate: "0.05",
      maxTrades: "30",
      durationSeconds: "900",
      feeRate: COST_DEFAULTS.feeRate,
      slippageRate: COST_DEFAULTS.slippageRate,
      allocationId: "",
      portfolioMaxLossRate: "",
      portfolioMaxLossAmount: "",
      perSymbolMaxWeight: "",
      decisionLogMode: "full_audit",
      takeProfitPercent: "0.005",
      stopLossPercent: "0.01",
    },
  },
  {
    id: "quick_paper",
    label: "2 · Quick paper session",
    description:
      "Short realistic paper run on 5m. Modest profit/loss caps and TP/SL so you can see a normal session lifecycle. Does not change your strategy choice.",
    patch: {
      mode: "simulation",
      timeframe: "5m",
      startingCapital: "500",
      allocatedCapital: "500",
      maxPositionSize: "250",
      targetNetProfitRate: "0.01",
      maxSessionLossRate: "0.01",
      maxTrades: "20",
      durationSeconds: "3600",
      feeRate: COST_DEFAULTS.feeRate,
      slippageRate: COST_DEFAULTS.slippageRate,
      allocationId: "",
      portfolioMaxLossRate: "",
      portfolioMaxLossAmount: "",
      perSymbolMaxWeight: "",
      decisionLogMode: "important_only",
      takeProfitPercent: "0.02",
      stopLossPercent: "0.01",
    },
  },
  {
    id: "conservative",
    label: "3 · Conservative longer run",
    description:
      "Slower 1h candles, smaller position vs capital, tighter session risk, no TP/SL. Better for overnight-style paper checks. Does not change your strategy choice.",
    patch: {
      mode: "simulation",
      timeframe: "1h",
      startingCapital: "1000",
      allocatedCapital: "500",
      maxPositionSize: "200",
      targetNetProfitRate: "0.005",
      maxSessionLossRate: "0.005",
      maxTrades: "10",
      durationSeconds: "14400",
      feeRate: COST_DEFAULTS.feeRate,
      slippageRate: COST_DEFAULTS.slippageRate,
      allocationId: "",
      portfolioMaxLossRate: "",
      portfolioMaxLossAmount: "",
      perSymbolMaxWeight: "",
      decisionLogMode: "important_only",
      takeProfitPercent: "",
      stopLossPercent: "",
    },
  },
  {
    id: "custom",
    label: "4 · Custom",
    description:
      "Keep or edit risk/capital fields yourself (also selected automatically after any manual change to those fields).",
  },
];

export function getSessionPreset(id: SessionPresetId): SessionPreset {
  return (
    SESSION_PRESETS.find((p) => p.id === id) ??
    SESSION_PRESETS[SESSION_PRESETS.length - 1]
  );
}
