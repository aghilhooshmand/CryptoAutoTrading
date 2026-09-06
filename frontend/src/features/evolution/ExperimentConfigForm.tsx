import { useMemo, useState, type FormEvent } from "react";
import type { ExperimentConfigBody } from "./evolutionApi";

const LEAF_OPTIONS = ["dual_ema", "rsi", "macd"] as const;
const OP_OPTIONS = ["and", "or", "vote"] as const;

/** Product-safe discrete alternatives (mirrors backend DEFAULT_PARAM_ALTS). */
const PARAM_ALT_CATALOGUE: Record<string, { label: string; options: number[] }> = {
  "rsi.period": { label: "RSI period", options: [7, 10, 14, 21] },
  "dual_ema.fastPeriod": { label: "Dual EMA fast", options: [5, 9, 12] },
  "dual_ema.slowPeriod": { label: "Dual EMA slow", options: [13, 21, 26] },
  "macd.fastPeriod": { label: "MACD fast", options: [8, 12] },
  "macd.slowPeriod": { label: "MACD slow", options: [17, 26] },
  "macd.signalPeriod": { label: "MACD signal", options: [5, 9] },
};

function defaultSelectedAlts(): Record<string, number[]> {
  const out: Record<string, number[]> = {};
  for (const [key, meta] of Object.entries(PARAM_ALT_CATALOGUE)) {
    out[key] = [...meta.options];
  }
  return out;
}

type Props = {
  disabled?: boolean;
  onStart: (body: ExperimentConfigBody) => void;
  onCancel?: () => void;
  canCancel?: boolean;
};

export function ExperimentConfigForm({ disabled, onStart, onCancel, canCancel }: Props) {
  const [populationSize, setPopulationSize] = useState(6);
  const [nGenerations, setNGenerations] = useState(3);
  const [seed, setSeed] = useState(7);
  const [fitnessId, setFitnessId] = useState("net_minus_bh");
  const [trainRatio, setTrainRatio] = useState(0.6);
  const [valRatio, setValRatio] = useState(0.2);
  const [testRatio, setTestRatio] = useState(0.2);
  const [symbol, setSymbol] = useState("btc_usdt");
  const [timeframe, setTimeframe] = useState("1h");
  const [startTime, setStartTime] = useState("2024-01-01T00:00:00Z");
  const [endTime, setEndTime] = useState("2024-06-01T00:00:00Z");
  const [leaves, setLeaves] = useState<string[]>(["dual_ema", "rsi", "macd"]);
  const [ops, setOps] = useState<string[]>(["and", "or", "vote"]);
  const [paramAlts, setParamAlts] = useState<Record<string, number[]>>(defaultSelectedAlts);
  const [error, setError] = useState<string | null>(null);

  const visibleParamKeys = useMemo(() => {
    return Object.keys(PARAM_ALT_CATALOGUE).filter((key) => {
      const leaf = key.split(".")[0];
      return leaves.includes(leaf);
    });
  }, [leaves]);

  function toggle(list: string[], value: string, setter: (v: string[]) => void) {
    if (list.includes(value)) setter(list.filter((x) => x !== value));
    else setter([...list, value]);
  }

  function toggleParamAlt(key: string, value: number) {
    setParamAlts((prev) => {
      const cur = prev[key] ?? [];
      const next = cur.includes(value) ? cur.filter((x) => x !== value) : [...cur, value].sort((a, b) => a - b);
      return { ...prev, [key]: next };
    });
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (leaves.length === 0) {
      setError("Select at least one strategy leaf");
      return;
    }
    if (Math.abs(trainRatio + valRatio + testRatio - 1) > 1e-6) {
      setError("Split ratios must sum to 1");
      return;
    }
    for (const key of visibleParamKeys) {
      if (!paramAlts[key]?.length) {
        setError(`Select at least one alternative for ${PARAM_ALT_CATALOGUE[key].label}`);
        return;
      }
    }
    const paramAlternatives: Record<string, number[]> = {};
    for (const key of visibleParamKeys) {
      paramAlternatives[key] = paramAlts[key];
    }
    onStart({
      symbol,
      timeframe,
      startTime,
      endTime,
      populationSize,
      nGenerations,
      seed,
      fitnessId,
      trainRatio,
      valRatio,
      testRatio,
      leaves,
      compositionOps: ops,
      paramAlternatives,
    });
  }

  return (
    <form className="evolution-config" onSubmit={submit} data-testid="evolution-config-form">
      <div className="backtest-field-row">
        <label>
          Population
          <input
            type="number"
            min={2}
            value={populationSize}
            disabled={disabled}
            onChange={(e) => setPopulationSize(Number(e.target.value))}
            data-testid="evolution-pop"
          />
        </label>
        <label>
          Generations
          <input
            type="number"
            min={1}
            value={nGenerations}
            disabled={disabled}
            onChange={(e) => setNGenerations(Number(e.target.value))}
            data-testid="evolution-ngen"
          />
        </label>
        <label>
          Seed
          <input
            type="number"
            value={seed}
            disabled={disabled}
            onChange={(e) => setSeed(Number(e.target.value))}
            data-testid="evolution-seed"
          />
        </label>
        <label>
          Fitness
          <select
            value={fitnessId}
            disabled={disabled}
            onChange={(e) => setFitnessId(e.target.value)}
            data-testid="evolution-fitness"
          >
            <option value="net_minus_bh">net − buy&amp;hold</option>
            <option value="net_profit">net profit</option>
          </select>
        </label>
      </div>
      <div className="backtest-field-row">
        <label>
          Symbol
          <input value={symbol} disabled={disabled} onChange={(e) => setSymbol(e.target.value)} />
        </label>
        <label>
          Timeframe
          <input
            value={timeframe}
            disabled={disabled}
            onChange={(e) => setTimeframe(e.target.value)}
          />
        </label>
        <label>
          Start
          <input
            value={startTime}
            disabled={disabled}
            onChange={(e) => setStartTime(e.target.value)}
            data-testid="evolution-start"
          />
        </label>
        <label>
          End
          <input
            value={endTime}
            disabled={disabled}
            onChange={(e) => setEndTime(e.target.value)}
            data-testid="evolution-end"
          />
        </label>
      </div>
      <div className="backtest-field-row">
        <label>
          Train
          <input
            type="number"
            step="0.05"
            value={trainRatio}
            disabled={disabled}
            onChange={(e) => setTrainRatio(Number(e.target.value))}
          />
        </label>
        <label>
          Val
          <input
            type="number"
            step="0.05"
            value={valRatio}
            disabled={disabled}
            onChange={(e) => setValRatio(Number(e.target.value))}
          />
        </label>
        <label>
          Test
          <input
            type="number"
            step="0.05"
            value={testRatio}
            disabled={disabled}
            onChange={(e) => setTestRatio(Number(e.target.value))}
          />
        </label>
      </div>
      <fieldset data-testid="evolution-leaves">
        <legend>Strategy leaves</legend>
        {LEAF_OPTIONS.map((id) => (
          <label key={id} style={{ marginRight: "1rem" }}>
            <input
              type="checkbox"
              checked={leaves.includes(id)}
              disabled={disabled}
              onChange={() => toggle(leaves, id, setLeaves)}
            />{" "}
            {id}
          </label>
        ))}
      </fieldset>
      <fieldset data-testid="evolution-ops">
        <legend>Composition operators</legend>
        {OP_OPTIONS.map((id) => (
          <label key={id} style={{ marginRight: "1rem" }}>
            <input
              type="checkbox"
              checked={ops.includes(id)}
              disabled={disabled}
              onChange={() => toggle(ops, id, setOps)}
            />{" "}
            {id}
          </label>
        ))}
      </fieldset>
      <fieldset data-testid="evolution-param-alts">
        <legend>Discrete parameter alternatives</legend>
        {visibleParamKeys.map((key) => {
          const meta = PARAM_ALT_CATALOGUE[key];
          const selected = paramAlts[key] ?? [];
          return (
            <div key={key} style={{ marginBottom: "0.5rem" }}>
              <span>{meta.label}: </span>
              {meta.options.map((opt) => (
                <label key={opt} style={{ marginRight: "0.75rem" }}>
                  <input
                    type="checkbox"
                    checked={selected.includes(opt)}
                    disabled={disabled}
                    onChange={() => toggleParamAlt(key, opt)}
                    data-testid={`evolution-param-${key}-${opt}`}
                  />{" "}
                  {opt}
                </label>
              ))}
            </div>
          );
        })}
      </fieldset>
      {error ? (
        <p className="form-error" role="alert" data-testid="evolution-config-error">
          {error}
        </p>
      ) : null}
      <div className="backtest-field-row">
        <button type="submit" disabled={disabled} data-testid="evolution-start-btn">
          Start evolution
        </button>
        {canCancel ? (
          <button type="button" onClick={onCancel} data-testid="evolution-cancel-btn">
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}
