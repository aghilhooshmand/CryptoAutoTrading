import { useEffect, useMemo, useState, type ReactNode } from "react";

import {
  FALLBACK_STRATEGIES,
  defaultParamsFor,
  listStrategies,
  type StrategyInfo,
  type StrategyParamValue,
  validateStrategyParamsClient,
} from "../../services/strategiesApi";

export interface StrategyConfigValue {
  strategyId: string;
  strategyParams: Record<string, StrategyParamValue>;
}

interface Props {
  disabled?: boolean;
  value: StrategyConfigValue;
  onChange: (next: StrategyConfigValue) => void;
  onValidationError?: (message: string | null) => void;
  /** Visual shell: simulation sits inside a card; backtest matches fieldset sections. */
  variant?: "simulation" | "backtest";
}

function paramLabel(name: string, fallback: string): string {
  if (name === "fastPeriod") return "Fast period";
  if (name === "slowPeriod") return "Slow period";
  return fallback;
}

function FieldHint({ children }: { children: ReactNode }) {
  return <span className="field-hint">{children}</span>;
}

export function StrategyConfigFields({
  disabled = false,
  value,
  onChange,
  onValidationError,
  variant = "simulation",
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
          setLoadError("Using built-in strategy defaults (strategy list unavailable).");
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
    onChange({ strategyId: id, strategyParams: defaultParamsFor(strat) });
  }

  function setParam(name: string, raw: string, type: StrategyInfo["parameters"][0]["type"]) {
    let next: StrategyParamValue;
    if (type === "decimal_string" || type === "string") {
      next = raw;
    } else {
      const n = Number(raw);
      next = Number.isFinite(n) ? n : (value.strategyParams[name] ?? 0);
    }
    onChange({
      ...value,
      strategyParams: {
        ...value.strategyParams,
        [name]: next,
      },
    });
  }

  if (!selected) {
    return <p className="note">No strategies registered.</p>;
  }

  const single = strategies.length === 1;
  const shellClass =
    variant === "backtest"
      ? "strategy-config strategy-config--backtest"
      : "strategy-config strategy-config--simulation";

  return (
    <div className={shellClass} data-testid="strategy-config-fields">
      <div className="strategy-config__head">
        <h3 className="strategy-config__title">Strategy</h3>
        <p className="strategy-config__subtitle">
          Advisory signals only — Controller and Risk still approve fills.
        </p>
      </div>

      {loadError ? <p className="hint">{loadError}</p> : null}

      <div className="strategy-config__grid">
        <div className="strategy-config__strategy">
          <span className="strategy-config__label">Rule</span>
          {single ? (
            <>
              <div
                className="strategy-config__pill"
                data-testid="strategy-id"
                data-strategy-id={selected.id}
              >
                {selected.displayName}
              </div>
              <FieldHint>Closed-candle Dual EMA crossover. Edit periods below.</FieldHint>
            </>
          ) : (
            <select
              data-testid="strategy-id"
              data-strategy-id={selected.id}
              value={selected.id}
              disabled={disabled}
              onChange={(e) => selectStrategy(e.target.value)}
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.displayName}
                </option>
              ))}
            </select>
          )}
        </div>

        {selected.parameters.map((p) => {
          const current = value.strategyParams[p.name] ?? p.default;
          const isDecimal = p.type === "decimal_string";
          return (
            <label key={p.name}>
              <span className="strategy-config__label">{paramLabel(p.name, p.label)}</span>
              <input
                type={isDecimal ? "text" : "number"}
                inputMode={isDecimal ? "decimal" : "numeric"}
                data-testid={`strategy-param-${p.name}`}
                data-param-type={p.type}
                value={current}
                min={isDecimal ? undefined : p.minimum}
                max={isDecimal ? undefined : p.maximum}
                step={isDecimal ? "any" : 1}
                disabled={disabled}
                onChange={(e) => setParam(p.name, e.target.value, p.type)}
              />
            </label>
          );
        })}
      </div>

      {clientError ? (
        <p className="error strategy-config__error" data-testid="strategy-param-error" role="alert">
          {clientError}
        </p>
      ) : null}
    </div>
  );
}

export function defaultStrategyConfig(): StrategyConfigValue {
  const s = FALLBACK_STRATEGIES[0];
  return {
    strategyId: s.id,
    strategyParams: defaultParamsFor(s),
  };
}
