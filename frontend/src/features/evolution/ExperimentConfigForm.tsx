import { useMemo, useState, type FormEvent } from "react";
import type { ExperimentConfigBody } from "./evolutionApi";
import {
  PARAM_ALT_CATALOGUE,
  buildBnfPreview,
  defaultParamTexts,
  parseParamList,
} from "./grammarPreview";

const LEAF_OPTIONS = ["dual_ema", "rsi", "macd"] as const;
const OP_OPTIONS = ["and", "or", "vote"] as const;
const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;

/** Parse datetime-local value to epoch ms (same as Backtest). */
function toMs(localValue: string): number | null {
  if (!localValue) return null;
  const ms = Date.parse(localValue);
  return Number.isFinite(ms) ? ms : null;
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
  const [startLocal, setStartLocal] = useState("2024-01-01T00:00");
  const [endLocal, setEndLocal] = useState("2024-06-01T00:00");
  const [leaves, setLeaves] = useState<string[]>(["dual_ema", "rsi", "macd"]);
  const [ops, setOps] = useState<string[]>(["and", "or", "vote"]);
  const [paramTexts, setParamTexts] = useState<Record<string, string>>(defaultParamTexts);
  const [customBnfEnabled, setCustomBnfEnabled] = useState(false);
  const [customBnf, setCustomBnf] = useState("");
  const [error, setError] = useState<string | null>(null);

  const visibleParamKeys = useMemo(() => {
    return Object.keys(PARAM_ALT_CATALOGUE).filter((key) => {
      const leaf = key.split(".")[0];
      return leaves.includes(leaf);
    });
  }, [leaves]);

  const parsedParams = useMemo(() => {
    const out: Record<string, number[]> = {};
    for (const key of Object.keys(PARAM_ALT_CATALOGUE)) {
      out[key] = parseParamList(paramTexts[key] ?? "");
    }
    return out;
  }, [paramTexts]);

  const builtBnf = useMemo(
    () => buildBnfPreview(leaves, ops, parsedParams),
    [leaves, ops, parsedParams],
  );

  const displayBnf = customBnfEnabled ? customBnf : builtBnf;

  function toggle(list: string[], value: string, setter: (v: string[]) => void) {
    if (list.includes(value)) setter(list.filter((x) => x !== value));
    else setter([...list, value]);
  }

  function setParamText(key: string, value: string) {
    setParamTexts((prev) => ({ ...prev, [key]: value }));
  }

  function appendSuggestion(key: string, value: number) {
    const cur = parseParamList(paramTexts[key] ?? "");
    if (cur.includes(value)) return;
    const next = [...cur, value].sort((a, b) => a - b);
    setParamText(key, next.join(", "));
  }

  function enableCustomBnf(checked: boolean) {
    setCustomBnfEnabled(checked);
    if (checked && !customBnf.trim()) {
      setCustomBnf(builtBnf);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const startMs = toMs(startLocal);
    const endMs = toMs(endLocal);
    if (startMs == null || endMs == null) {
      setError("Start and end are required");
      return;
    }
    if (endMs <= startMs) {
      setError("End must be after start");
      return;
    }
    if (!customBnfEnabled && leaves.length === 0) {
      setError("Select at least one strategy leaf");
      return;
    }
    if (Math.abs(trainRatio + valRatio + testRatio - 1) > 1e-6) {
      setError("Split ratios must sum to 1");
      return;
    }
    if (customBnfEnabled) {
      if (!customBnf.trim()) {
        setError("Custom grammar BNF is empty");
        return;
      }
    } else {
      for (const key of visibleParamKeys) {
        if (!parsedParams[key]?.length) {
          setError(
            `Enter at least one number for ${PARAM_ALT_CATALOGUE[key].label} (e.g. 7, 14, 21)`,
          );
          return;
        }
      }
    }

    const paramAlternatives: Record<string, number[]> = {};
    for (const key of visibleParamKeys) {
      paramAlternatives[key] = parsedParams[key];
    }

    const body: ExperimentConfigBody = {
      symbol,
      timeframe,
      startTime: new Date(startMs).toISOString(),
      endTime: new Date(endMs).toISOString(),
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
    };
    if (customBnfEnabled) {
      body.grammarBnf = customBnf;
    }
    onStart(body);
  }

  return (
    <form
      className="backtest-config"
      onSubmit={submit}
      data-testid="evolution-config-form"
    >
      <h3 className="visually-hidden">Evolution experiment configuration</h3>

      <fieldset className="backtest-fieldset" disabled={disabled}>
        <legend>Market window</legend>
        <div className="backtest-field-row">
          <label>
            Symbol
            <input
              value={symbol}
              disabled={disabled}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="btc_usdt"
            />
          </label>
          <label>
            Timeframe
            <select
              value={timeframe}
              disabled={disabled}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              {INTERVALS.map((iv) => (
                <option key={iv} value={iv}>
                  {iv}
                </option>
              ))}
            </select>
          </label>
          <label>
            Start
            <input
              type="datetime-local"
              value={startLocal}
              disabled={disabled}
              onChange={(e) => setStartLocal(e.target.value)}
              required
              data-testid="evolution-start"
            />
          </label>
          <label>
            End
            <input
              type="datetime-local"
              value={endLocal}
              disabled={disabled}
              onChange={(e) => setEndLocal(e.target.value)}
              required
              data-testid="evolution-end"
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={disabled}>
        <legend>Search parameters</legend>
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
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={disabled}>
        <legend>Train / validation / test split</legend>
        <p className="field-hint">Ratios must sum to 1.</p>
        <div className="backtest-field-row">
          <label>
            Train
            <input
              type="number"
              step="0.05"
              min={0}
              max={1}
              value={trainRatio}
              disabled={disabled}
              onChange={(e) => setTrainRatio(Number(e.target.value))}
            />
          </label>
          <label>
            Validation
            <input
              type="number"
              step="0.05"
              min={0}
              max={1}
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
              min={0}
              max={1}
              value={testRatio}
              disabled={disabled}
              onChange={(e) => setTestRatio(Number(e.target.value))}
            />
          </label>
        </div>
      </fieldset>

      <fieldset
        className="backtest-fieldset"
        disabled={disabled || customBnfEnabled}
        data-testid="evolution-leaves"
      >
        <legend>Strategy leaves</legend>
        <div className="evolution-check-grid">
          {LEAF_OPTIONS.map((id) => (
            <label key={id} className="evolution-check">
              <input
                type="checkbox"
                checked={leaves.includes(id)}
                disabled={disabled || customBnfEnabled}
                onChange={() => toggle(leaves, id, setLeaves)}
              />
              <span>{id}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset
        className="backtest-fieldset"
        disabled={disabled || customBnfEnabled}
        data-testid="evolution-ops"
      >
        <legend>Composition operators</legend>
        <div className="evolution-check-grid">
          {OP_OPTIONS.map((id) => (
            <label key={id} className="evolution-check">
              <input
                type="checkbox"
                checked={ops.includes(id)}
                disabled={disabled || customBnfEnabled}
                onChange={() => toggle(ops, id, setOps)}
              />
              <span>{id}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset
        className="backtest-fieldset"
        disabled={disabled || customBnfEnabled}
        data-testid="evolution-param-alts"
      >
        <legend>Parameter alternatives</legend>
        <p className="field-hint">
          Type comma-separated integers yourself (e.g. 7, 14, 21). Suggestions
          append a value when clicked.
        </p>
        <div className="evolution-param-groups">
          {visibleParamKeys.map((key) => {
            const meta = PARAM_ALT_CATALOGUE[key];
            return (
              <div key={key} className="evolution-param-group">
                <label>
                  {meta.label}
                  <input
                    value={paramTexts[key] ?? ""}
                    disabled={disabled || customBnfEnabled}
                    onChange={(e) => setParamText(key, e.target.value)}
                    placeholder={meta.suggestions.join(", ")}
                    data-testid={`evolution-param-text-${key}`}
                  />
                </label>
                <div className="evolution-check-grid">
                  {meta.suggestions.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      className="evolution-suggest"
                      disabled={disabled || customBnfEnabled}
                      onClick={() => appendSuggestion(key, opt)}
                      data-testid={`evolution-param-${key}-${opt}`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={disabled}>
        <legend>Final grammar (BNF)</legend>
        <p className="field-hint">
          Live preview of the grammar that will run. Enable custom edit only if
          you need to override the structured build.
        </p>
        <label className="evolution-check evolution-bnf-toggle">
          <input
            type="checkbox"
            checked={customBnfEnabled}
            disabled={disabled}
            onChange={(e) => enableCustomBnf(e.target.checked)}
            data-testid="evolution-bnf-override"
          />
          <span>Edit grammar manually (advanced)</span>
        </label>
        <textarea
          className="evolution-bnf"
          value={displayBnf}
          readOnly={!customBnfEnabled}
          disabled={disabled}
          spellCheck={false}
          rows={14}
          onChange={(e) => setCustomBnf(e.target.value)}
          data-testid="evolution-bnf-text"
          aria-label="Grammar BNF"
        />
      </fieldset>

      {error ? (
        <p className="form-error" role="alert" data-testid="evolution-config-error">
          {error}
        </p>
      ) : null}

      <div className="backtest-actions">
        <button type="submit" disabled={disabled} data-testid="evolution-start-btn">
          Start evolution
        </button>
        {canCancel ? (
          <button
            type="button"
            className="danger"
            onClick={onCancel}
            data-testid="evolution-cancel-btn"
          >
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}
