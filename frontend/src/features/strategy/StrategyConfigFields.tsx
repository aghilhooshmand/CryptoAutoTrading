import { useEffect, useMemo, useState } from "react";

import {
  FALLBACK_STRATEGIES,
  defaultParamsFor,
  listStrategies,
  type StrategyInfo,
  validateStrategyParamsClient,
} from "../../services/strategiesApi";

export interface StrategyConfigValue {
  strategyId: string;
  strategyParams: Record<string, number>;
}

interface Props {
  disabled?: boolean;
  value: StrategyConfigValue;
  onChange: (next: StrategyConfigValue) => void;
  onValidationError?: (message: string | null) => void;
}

export function StrategyConfigFields({
  disabled = false,
  value,
  onChange,
  onValidationError,
}: Props) {
  const [strategies, setStrategies] = useState<StrategyInfo[]>(FALLBACK_STRATEGIES);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listStrategies()
      .then((list) => {
        if (cancelled || list.length === 0) return;
        setStrategies(list);
        setLoadError(null);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Using built-in Dual EMA schema (strategy list unavailable).");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected =
    strategies.find((s) => s.id === value.strategyId) ?? strategies[0] ?? null;

  const clientError = useMemo(() => {
    if (!selected) return "No strategy available.";
    return validateStrategyParamsClient(selected, value.strategyParams);
  }, [selected, value.strategyParams]);

  useEffect(() => {
    onValidationError?.(clientError);
  }, [clientError, onValidationError]);

  function selectStrategy(id: string) {
    const strat = strategies.find((s) => s.id === id);
    if (!strat) return;
    const defaults = defaultParamsFor(strat);
    const params: Record<string, number> = {};
    for (const [k, v] of Object.entries(defaults)) {
      params[k] = Number(v);
    }
    onChange({ strategyId: id, strategyParams: params });
  }

  function setParam(name: string, raw: string) {
    const n = Number(raw);
    onChange({
      ...value,
      strategyParams: {
        ...value.strategyParams,
        [name]: Number.isFinite(n) ? n : (value.strategyParams[name] ?? 0),
      },
    });
  }

  if (!selected) {
    return <p className="note">No strategies registered.</p>;
  }

  return (
    <fieldset className="strategy-config" data-testid="strategy-config-fields" disabled={disabled}>
      <legend>Strategy</legend>
      {loadError ? <p className="hint">{loadError}</p> : null}
      <label>
        Strategy
        <select
          data-testid="strategy-id"
          value={selected.id}
          onChange={(e) => selectStrategy(e.target.value)}
        >
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>
              {s.displayName} ({s.id})
            </option>
          ))}
        </select>
      </label>
      {selected.parameters.map((p) => (
        <label key={p.name}>
          {p.label}
          <input
            type="number"
            data-testid={`strategy-param-${p.name}`}
            value={value.strategyParams[p.name] ?? p.default}
            min={p.minimum}
            max={p.maximum}
            step={1}
            onChange={(e) => setParam(p.name, e.target.value)}
          />
        </label>
      ))}
      {clientError ? (
        <p className="error" data-testid="strategy-param-error" role="alert">
          {clientError}
        </p>
      ) : null}
    </fieldset>
  );
}

export function defaultStrategyConfig(): StrategyConfigValue {
  const s = FALLBACK_STRATEGIES[0];
  const defaults = defaultParamsFor(s);
  return {
    strategyId: s.id,
    strategyParams: {
      fastPeriod: Number(defaults.fastPeriod),
      slowPeriod: Number(defaults.slowPeriod),
    },
  };
}
