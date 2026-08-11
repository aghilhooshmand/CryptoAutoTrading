/** Typed client for `GET /strategies`. */

export type StrategyParamType = "integer" | "decimal_string" | "string";

export interface StrategyParamDef {
  name: string;
  type: StrategyParamType;
  label: string;
  default: number | string;
  minimum?: number;
  maximum?: number;
}

export interface StrategyConstraint {
  code: string;
  message: string;
  fields: string[];
}

export interface StrategyInfo {
  id: string;
  displayName: string;
  aliases: string[];
  parameters: StrategyParamDef[];
  constraints: StrategyConstraint[];
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
}

/** Built-in Dual EMA schema used while loading / if list fails. */
export const FALLBACK_STRATEGIES: StrategyInfo[] = [
  {
    id: "dual_ema",
    displayName: "Dual EMA",
    aliases: ["dual_ema_9_21"],
    parameters: [
      {
        name: "fastPeriod",
        type: "integer",
        label: "Fast EMA period",
        default: 9,
        minimum: 1,
      },
      {
        name: "slowPeriod",
        type: "integer",
        label: "Slow EMA period",
        default: 21,
        minimum: 2,
      },
    ],
    constraints: [
      {
        code: "fast_lt_slow",
        message: "Fast period must be less than slow period.",
        fields: ["fastPeriod", "slowPeriod"],
      },
    ],
  },
];

export async function listStrategies(): Promise<StrategyInfo[]> {
  const res = await fetch("/strategies");
  if (!res.ok) {
    throw new Error(`Failed to list strategies (${res.status})`);
  }
  const data = (await res.json()) as StrategiesResponse;
  return data.strategies ?? [];
}

export function defaultParamsFor(strategy: StrategyInfo): Record<string, number | string> {
  const out: Record<string, number | string> = {};
  for (const p of strategy.parameters) {
    out[p.name] = p.default;
  }
  return out;
}

export function validateStrategyParamsClient(
  strategy: StrategyInfo,
  params: Record<string, number | string>,
): string | null {
  for (const p of strategy.parameters) {
    const raw = params[p.name];
    const n = Number(raw);
    if (!Number.isInteger(n)) {
      return `${p.label} must be an integer.`;
    }
    if (p.minimum != null && n < p.minimum) {
      return `${p.label} must be ≥ ${p.minimum}.`;
    }
    if (p.maximum != null && n > p.maximum) {
      return `${p.label} must be ≤ ${p.maximum}.`;
    }
  }
  for (const c of strategy.constraints) {
    if (c.code === "fast_lt_slow") {
      const fast = Number(params.fastPeriod);
      const slow = Number(params.slowPeriod);
      if (!(fast < slow)) {
        return c.message;
      }
    }
  }
  return null;
}
