/** Typed client for `GET /strategies`. */

export type StrategyParamType = "integer" | "decimal_string" | "string";

export type StrategyParamValue = number | string;

export interface StrategyParamDef {
  name: string;
  type: StrategyParamType;
  label: string;
  default: StrategyParamValue;
  minimum?: number;
  maximum?: number;
  /** When true with ``minimum``, value must be strictly greater than minimum. */
  exclusiveMinimum?: boolean;
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

export function defaultParamsFor(strategy: StrategyInfo): Record<string, StrategyParamValue> {
  const out: Record<string, StrategyParamValue> = {};
  for (const p of strategy.parameters) {
    out[p.name] = p.default;
  }
  return out;
}

function validateOneParam(
  p: StrategyParamDef,
  raw: StrategyParamValue | undefined,
): string | null {
  if (raw === undefined || raw === null || raw === "") {
    return `${p.label} is required.`;
  }
  if (p.type === "decimal_string") {
    const text = String(raw).trim();
    const n = Number(text);
    if (!Number.isFinite(n) || text === "") {
      return `${p.label} must be a decimal number.`;
    }
    if (p.minimum != null) {
      if (p.exclusiveMinimum) {
        if (!(n > p.minimum)) {
          return `${p.label} must be > ${p.minimum}.`;
        }
      } else if (n < p.minimum) {
        return `${p.label} must be ≥ ${p.minimum}.`;
      }
    }
    if (p.maximum != null && n > p.maximum) {
      return `${p.label} must be ≤ ${p.maximum}.`;
    }
    return null;
  }
  if (p.type === "integer") {
    const n = Number(raw);
    if (!Number.isInteger(n)) {
      return `${p.label} must be an integer.`;
    }
    if (p.minimum != null) {
      if (p.exclusiveMinimum) {
        if (!(n > p.minimum)) {
          return `${p.label} must be > ${p.minimum}.`;
        }
      } else if (n < p.minimum) {
        return `${p.label} must be ≥ ${p.minimum}.`;
      }
    }
    if (p.maximum != null && n > p.maximum) {
      return `${p.label} must be ≤ ${p.maximum}.`;
    }
    return null;
  }
  return null;
}

export function validateStrategyParamsClient(
  strategy: StrategyInfo,
  params: Record<string, StrategyParamValue>,
): string | null {
  for (const p of strategy.parameters) {
    const err = validateOneParam(p, params[p.name]);
    if (err) return err;
  }
  for (const c of strategy.constraints) {
    if (c.code === "fast_lt_slow") {
      const fast = Number(params.fastPeriod);
      const slow = Number(params.slowPeriod);
      if (!(fast < slow)) {
        return c.message;
      }
    }
    if (c.code === "oversold_lt_overbought") {
      const oversold = Number(params.oversold);
      const overbought = Number(params.overbought);
      if (!(oversold < overbought)) {
        return c.message;
      }
    }
  }
  return null;
}
