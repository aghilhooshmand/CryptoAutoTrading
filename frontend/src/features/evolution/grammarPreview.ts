/** Client-side BNF preview mirroring backend grammar_builder (Feature 020b). */

export const PARAM_ALT_CATALOGUE: Record<string, { label: string; suggestions: number[] }> = {
  "rsi.period": { label: "RSI period", suggestions: [7, 10, 14, 21] },
  "dual_ema.fastPeriod": { label: "Dual EMA fast", suggestions: [5, 9, 12] },
  "dual_ema.slowPeriod": { label: "Dual EMA slow", suggestions: [13, 21, 26] },
  "macd.fastPeriod": { label: "MACD fast", suggestions: [8, 12] },
  "macd.slowPeriod": { label: "MACD slow", suggestions: [17, 26] },
  "macd.signalPeriod": { label: "MACD signal", suggestions: [5, 9] },
};

export function defaultParamTexts(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, meta] of Object.entries(PARAM_ALT_CATALOGUE)) {
    out[key] = meta.suggestions.join(", ");
  }
  return out;
}

/** Parse "7, 10, 14" → numbers; empty / invalid tokens dropped. */
export function parseParamList(text: string): number[] {
  return text
    .split(/[,|\s]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isFinite(n) && n >= 1)
    .map((n) => Math.trunc(n));
}

function alts(values: number[]): string {
  return values.map((v) => String(v)).join(" | ");
}

export function buildBnfPreview(
  leaves: string[],
  ops: string[],
  paramAlts: Record<string, number[]>,
): string {
  const leafForms: string[] = [];
  const paramLines: string[] = [];

  if (leaves.includes("rsi")) {
    leafForms.push("rsi(period=<rsi_period>, oversold=30, overbought=70)");
    paramLines.push(
      `<rsi_period> ::= ${alts(paramAlts["rsi.period"]?.length ? paramAlts["rsi.period"] : [14])}`,
    );
  }
  if (leaves.includes("dual_ema")) {
    leafForms.push("dual_ema(fastPeriod=<ema_fast>, slowPeriod=<ema_slow>)");
    paramLines.push(
      `<ema_fast> ::= ${alts(paramAlts["dual_ema.fastPeriod"]?.length ? paramAlts["dual_ema.fastPeriod"] : [9])}`,
    );
    paramLines.push(
      `<ema_slow> ::= ${alts(paramAlts["dual_ema.slowPeriod"]?.length ? paramAlts["dual_ema.slowPeriod"] : [21])}`,
    );
  }
  if (leaves.includes("macd")) {
    leafForms.push(
      "macd(fastPeriod=<macd_fast>, slowPeriod=<macd_slow>, signalPeriod=<macd_sig>)",
    );
    paramLines.push(
      `<macd_fast> ::= ${alts(paramAlts["macd.fastPeriod"]?.length ? paramAlts["macd.fastPeriod"] : [12])}`,
    );
    paramLines.push(
      `<macd_slow> ::= ${alts(paramAlts["macd.slowPeriod"]?.length ? paramAlts["macd.slowPeriod"] : [26])}`,
    );
    paramLines.push(
      `<macd_sig> ::= ${alts(paramAlts["macd.signalPeriod"]?.length ? paramAlts["macd.signalPeriod"] : [9])}`,
    );
  }

  if (!leafForms.length) {
    return "# Select at least one strategy leaf to preview grammar.\n";
  }

  const composeForms = ops.map((op) => `${op}(<leaf>, <leaf>)`);
  const program = composeForms.length ? "<leaf> | <compose>" : "<leaf>";
  const composeBlock = composeForms.length
    ? `<compose> ::= ${composeForms.join(" | ")}\n`
    : "";

  return [
    "# Final grammar (BNF) — built from leaves / ops / param lists.",
    `<program> ::= ${program}`,
    composeBlock.trimEnd(),
    `<leaf> ::= ${leafForms.join(" | ")}`,
    ...paramLines,
    "",
  ]
    .filter((line, i, arr) => !(line === "" && arr[i - 1] === ""))
    .join("\n");
}
